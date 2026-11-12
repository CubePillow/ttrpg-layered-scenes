"""Turn transparent layers into one big-pixel style, without AI.

All layers share one grid and one palette:
  1. the palette is taken from all layers together (k-means in Lab colour space)
  2. every block of `block` x `block` pixels becomes one pixel with the block's most frequent palette colour
  3. a block is opaque when more than half of it was opaque, otherwise transparent

Used by POST /pixelize (main.py). From the command line, first file = background:
    python pixelize.py background.png tower.png tree.png --block 4 --colors 16 --out pixel_assets
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

OPAQUE = 127


def build_palette(layers: list[Image.Image], colors: int) -> np.ndarray:
    """Palette in Lab, shape (n, 3). Rare colours count more than their area, so a small flame keeps its colour."""
    pixels = [np.asarray(l)[..., :3][np.asarray(l)[..., 3] > OPAQUE] for l in layers]
    pixels = np.concatenate(pixels) if pixels else np.zeros((0, 3), np.uint8)
    if len(pixels) == 0:
        return np.zeros((1, 3), np.float32)
    bins, counts = np.unique(pixels >> 3, axis=0, return_counts=True)
    weight = np.maximum(1, np.sqrt(counts) / 4).astype(int)
    rgb = np.repeat((bins << 3) + 4, weight, axis=0).astype(np.uint8)
    lab = cv2.cvtColor(rgb[None], cv2.COLOR_RGB2LAB)[0].astype(np.float32)
    k = min(colors, len(bins))
    if k == len(bins):
        return np.unique(lab, axis=0)
    cv2.setRNGSeed(1)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, _, centers = cv2.kmeans(lab, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    return centers


def pixelize(layers: list[Image.Image], block: int = 4, colors: int = 16) -> list[Image.Image]:
    """Layers in (any size, resized to the first one), small RGBA layers out: 1 block = 1 pixel."""
    if not layers:
        return []
    size = layers[0].size
    layers = [l.convert("RGBA") if l.size == size else l.convert("RGBA").resize(size) for l in layers]
    gw, gh = max(1, size[0] // block), max(1, size[1] // block)
    palette = build_palette(layers, colors)
    palette_rgb = cv2.cvtColor(palette[None].astype(np.uint8), cv2.COLOR_LAB2RGB)[0]
    out = []
    for layer in layers:
        a = np.asarray(layer.crop((0, 0, gw * block, gh * block)))
        lab = cv2.cvtColor(np.ascontiguousarray(a[..., :3]), cv2.COLOR_RGB2LAB).astype(np.float32)
        index = np.argmin(((lab[:, :, None] - palette[None, None]) ** 2).sum(-1), axis=-1)
        solid = a[..., 3] > OPAQUE
        votes = np.zeros((gh, gw, len(palette)), np.int32)
        for c in range(len(palette)):
            votes[..., c] = ((index == c) & solid).reshape(gh, block, gw, block).sum((1, 3))
        small = np.zeros((gh, gw, 4), np.uint8)
        small[..., :3] = palette_rgb[votes.argmax(-1)]
        small[..., 3] = np.where(solid.reshape(gh, block, gw, block).mean((1, 3)) > 0.5, 255, 0)
        out.append(Image.fromarray(small))
    return out


def trim(layer: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    """Cut away the empty border. Returns the cut layer and its (x, y) on the grid."""
    box = layer.getchannel("A").getbbox() or (0, 0, 1, 1)
    return layer.crop(box), (box[0], box[1])


def used_colors(layers: list[Image.Image]) -> list[str]:
    colors = set()
    for layer in layers:
        a = np.asarray(layer.convert("RGBA"))
        for r, g, b in np.unique(a[a[..., 3] > 0][:, :3], axis=0):
            colors.add(f"#{r:02x}{g:02x}{b:02x}")
    return sorted(colors)


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Pixelize layer files; the first file is the background.")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--block", type=int, default=4)
    ap.add_argument("--colors", type=int, default=16)
    ap.add_argument("--out", default="pixel_assets")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    small = pixelize([Image.open(p) for p in args.images], args.block, args.colors)
    items = []
    for depth, (path, layer) in enumerate(zip(args.images, small)):
        name = Path(path).stem.split("__")[0]
        cut, (x, y) = trim(layer)
        cut.save(out / f"{name}.png")
        items.append({"name": name, "file": f"{name}.png", "depth": depth, "x": x, "y": y, "width": cut.width, "height": cut.height})
    info = {"grid": list(small[0].size), "block": args.block, "palette": used_colors(small), "layers": items}
    (out / "assets.json").write_text(json.dumps(info, indent=1))
    print(f"saved {len(items)} layers to {out}")
