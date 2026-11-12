"""Image layer test: pixelize every layer picture in tests/image through POST /pixelize.

Put PNG files into tests/image (for example layers the prototype split) and run `python -m pytest`.
The folder is not in git; without pictures this test is skipped.
Pictures of the same size are sent together, so they get one shared grid and one shared palette.
Results go to tests/output/: <name>.png (1 block = 1 pixel, cut to its content), <name>_preview.png (enlarged)
and _compare_<width>x<height>.png, which shows every original next to its pixel version.
"""
import base64
import io
from collections import defaultdict
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app

IMAGES = Path(__file__).parent / "image"
OUTPUT = Path(__file__).parent / "output"
BLOCK, COLORS = 4, 16

IMAGES.mkdir(exist_ok=True)  # the folder is not in git, so make it on first run

client = TestClient(app)


def groups():
    """Files grouped by picture size; a file named background* goes first (it is the back layer)."""
    by_size = defaultdict(list)
    for path in sorted(IMAGES.glob("*.png"), key=lambda p: (not p.stem.startswith("background"), p.name)):
        by_size[Image.open(path).size].append(path)
    return list(by_size.values())


def layer_names(files):
    """Name = the part of the file name before "__"; a repeated name gets -2, -3 ... so no result overwrites another."""
    names = []
    for f in files:
        base = f.stem.split("__")[0]
        same = sum(n == base or n.startswith(base + "-") and n[len(base) + 1:].isdigit() for n in names)
        names.append(base if same == 0 else f"{base}-{same + 1}")
    return names


def on_checker(image: Image.Image, tile: int) -> Image.Image:
    """The picture on a grey checkerboard, so transparent parts are visible."""
    y, x = np.mgrid[0:tile, 0:tile]
    board = np.where(((x // 16 + y // 16) % 2)[..., None] == 0, 205, 235).astype(np.uint8).repeat(3, axis=2)
    back = Image.fromarray(board).convert("RGBA")
    back.alpha_composite(image.convert("RGBA").resize((tile, tile), Image.NEAREST))
    return back.convert("RGB")


def compare_sheet(pairs, tile: int = 256, per_row: int = 3) -> Image.Image:
    """pairs = [(original, pixel version on the full grid)]. Each cell shows original | pixel version."""
    rows = -(-len(pairs) // per_row)
    gap = 12
    sheet = Image.new("RGB", (per_row * (2 * tile + gap) - gap, rows * (tile + gap) - gap), (40, 40, 40))
    for i, (original, pixel) in enumerate(pairs):
        x, y = (i % per_row) * (2 * tile + gap), (i // per_row) * (tile + gap)
        sheet.paste(on_checker(original, tile), (x, y))
        sheet.paste(on_checker(pixel, tile), (x + tile, y))
    return sheet


def test_there_are_image_layers_to_pixelize():
    if not groups():
        pytest.skip(f"no PNG files in {IMAGES}; the folder is not in git, put your own layer pictures there")


@pytest.mark.parametrize("files", groups(), ids=lambda files: f"{len(files)}-layers-starting-{files[0].stem[:20]}")
def test_image_layers_become_pixel_assets(files):
    size = Image.open(files[0]).size
    body = {"layers": [{"name": n, "image": base64.b64encode(f.read_bytes()).decode()} for n, f in zip(layer_names(files), files)],
            "block": BLOCK, "colors": COLORS}

    r = client.post("/pixelize", json=body)
    assert r.status_code == 200, r.text
    data = r.json()

    grid = (size[0] // BLOCK, size[1] // BLOCK)
    assert tuple(data["grid"]) == grid and len(data["layers"]) == len(files)
    OUTPUT.mkdir(exist_ok=True)
    colors = set()
    pairs = []
    for layer, file in zip(data["layers"], files):
        image = Image.open(io.BytesIO(base64.b64decode(layer["image"].split(",", 1)[1]))).convert("RGBA")
        a = np.asarray(image)
        assert image.size == (layer["width"], layer["height"])                        # cut to its content
        assert layer["x"] + layer["width"] <= grid[0] and layer["y"] + layer["height"] <= grid[1]
        assert set(np.unique(a[..., 3])) <= {0, 255}                                  # hard edges only
        assert (a[..., 3] > 0).any(), f"{layer['name']} came back empty"
        colors |= {f"#{r:02x}{g:02x}{b:02x}" for r, g, b in np.unique(a[a[..., 3] > 0][:, :3], axis=0)}
        image.save(OUTPUT / f"{layer['name']}.png")
        image.resize((image.width * BLOCK, image.height * BLOCK), Image.NEAREST).save(OUTPUT / f"{layer['name']}_preview.png")
        placed = Image.new("RGBA", grid, (0, 0, 0, 0))
        placed.paste(image, (layer["x"], layer["y"]))
        pairs.append((Image.open(file), placed))
    compare_sheet(pairs).save(OUTPUT / f"_compare_{size[0]}x{size[1]}.png")
    assert colors == set(data["palette"]) and len(colors) <= COLORS                   # one shared palette
