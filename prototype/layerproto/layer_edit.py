"""Edit one RGBA layer with a generative editor (Qwen-Image-2.1 RGBA edit, ...) and keep its transparency.

Measured on fox & cottage (docs/concepts/editing.md §5): the editor returned a fully opaque scene or an emptied layer on
6 of 10 first tries; accepting an edit only when the transparent share stays close to the input and retrying with the next
seed gave 10 of 10 accepted edits (4 on the second try).

    edited, report = edit_layer_keep_alpha(lambda img, seed: qwen21_edit(img, prompt, seed), layer_rgba, seeds=(42, 7, 123, 2024))
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
from PIL import Image


def transparent_share(img: Image.Image, thr: int = 16) -> float:
    return float((np.asarray(img.convert("RGBA"))[..., 3] < thr).mean())


def opaque_ratio(out: Image.Image, ref: Image.Image, thr: int = 16) -> float:
    """Visible area of `out` relative to `ref` (1.0 = same). Catches emptied or flooded small layers that the transparent
    share cannot (a 97 % transparent fox layer stays within 0.15 of 100 % transparent when it is wiped)."""
    a, b = (np.asarray(x.convert("RGBA"))[..., 3] >= thr for x in (out, ref))
    return float(a.sum()) / max(1.0, float(b.sum()))


def edit_layer_keep_alpha(editor: Callable[[Image.Image, int], Image.Image], layer: Image.Image,
                          seeds: Sequence[int] = (42, 7, 123, 2024), tol: float = 0.15,
                          lock_alpha: bool = False, min_visible: float = 0.4,
                          max_visible: float = 2.5) -> tuple[Image.Image, dict]:
    """Run `editor(layer, seed)` until the transparent share is within `tol` of the input's.

    Returns (edited layer, report). If no seed passes, the closest attempt is returned with report["accepted"] = False
    (the caller can then fall back to the unedited layer). lock_alpha=True also multiplies the edit's alpha by the
    input alpha, trimming spill outside the original shape (useful when the share is right but the outline drifted).
    """
    layer = layer.convert("RGBA")
    want = transparent_share(layer)
    best, best_err, tries = None, 1e9, []
    for seed in seeds:
        out = editor(layer, seed).convert("RGBA")
        if out.size != layer.size:
            out = out.resize(layer.size)
        err = abs(transparent_share(out) - want)
        ratio = opaque_ratio(out, layer)
        ok = err < tol and (min_visible <= ratio <= max_visible or transparent_share(layer) > 0.999)
        if not ok and err < tol:
            err = tol                                    # share fine but the visible area is wiped / flooded: not acceptable
        tries.append({"seed": seed, "transparent": round(transparent_share(out), 3), "visible_ratio": round(ratio, 2), "ok": ok})
        if err < best_err:
            best, best_err = out, err
        if ok:
            break
    if lock_alpha and best is not None:
        a = np.minimum(np.asarray(best.getchannel("A")), np.asarray(layer.getchannel("A")))
        best = best.copy()
        best.putalpha(Image.fromarray(a.astype(np.uint8)))
    return best, {"accepted": best_err < tol and any(t["ok"] for t in tries), "input_transparent": round(want, 3), "tries": tries}
