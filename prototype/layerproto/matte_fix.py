"""Halo / fringe fix for generated RGBA layers (Qwen-Image-2.1, LayerDiffuse, ART+ ...).

Generated objects are often premultiplied-looking: the semi-transparent edge pixels carry the colour of the background
they were drawn on (white or grey halo on a dark scene). Two steps, both CPU-only:
  1. decontaminate: replace the RGB of edge pixels (alpha below `solid`) with the colour of the nearest solid interior pixels
     (iterated masked blur / dilation), so the edge keeps the object's colour instead of the old background's;
  2. optionally shrink the alpha by `erode` pixels and re-feather, which removes the last bright rim.

    fixed = defringe(layer_rgba, solid=0.9, erode=1)
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def _blur(arr: np.ndarray, r: float) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    return np.stack([gaussian_filter(arr[..., i], r) for i in range(arr.shape[-1])], -1)


def defringe(layer: Image.Image, solid: float = 0.9, erode: int = 1, feather: float = 0.8, iters: int = 8) -> Image.Image:
    rgba = layer.convert("RGBA")
    arr = np.asarray(rgba, np.float32)
    rgb, a = arr[..., :3], arr[..., 3] / 255.0
    known = (a >= solid).astype(np.float32)               # pixels whose colour we trust
    colour = rgb * known[..., None]
    weight = known.copy()
    filled = known > 0
    out = rgb.copy()
    cur_c, cur_w = colour, weight
    for i in range(iters):                                # grow the trusted colour outwards, 2 px at a time
        bc = _blur(np.dstack([cur_c, cur_w]).astype(np.float32), 1.5 + i)
        w = bc[..., 3]
        est = bc[..., :3] / np.maximum(w[..., None], 1e-3)
        new = (~filled) & (w > 0.02)
        out[new] = est[new]
        filled |= new
        cur_c = np.where(filled[..., None], out, 0)
        cur_w = filled.astype(np.float32)
    edge = (a < solid) & (a > 0)
    out = np.where(edge[..., None], out, rgb)             # only touch the edge pixels
    alpha = (a * 255).astype(np.float32)
    if erode > 0:
        m = Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.MinFilter(2 * erode + 1))
        m = m.filter(ImageFilter.GaussianBlur(feather))
        alpha = np.minimum(alpha, np.asarray(m, np.float32) * 1.15)
    return Image.fromarray(np.dstack([out.clip(0, 255), alpha.clip(0, 255)]).astype(np.uint8), "RGBA")
