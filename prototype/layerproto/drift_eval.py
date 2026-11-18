"""Drift over long edit sequences: layered vs flat editing (gap G1).

Protocol (research_notes/Layered loop open paths/multi_turn_drift_evaluation.md, reports/Layered loop open paths.md):
  arm A "layered"      - edit only the target RGBA layer, recomposite; layers persist across turns
  arm B "flat"         - a flat image editor chains its own outputs (the usual multi-turn setting)
  arm C "redecompose"  - layered, but the composite is re-decomposed every turn (isolates decompose/recompose error)
Every turn is compared with turn 0:
  * outside-edit drift: PSNR / SSIM (and optional LPIPS, DINO) outside the union of every region edited so far
    (ImageDirector, UIST'26, used SSIM outside the old+new object masks; TailSteer measures PSNR outside the box)
  * per-layer: alpha IoU and alpha-weighted RGB L1 against the turn-0 layer (Qwen-Image-Layered / LayerD protocol)
  * global: mean luminance shift (flow editors brighten per turn, EdiVal-Agent)
Reported: per-turn curves, area under the curve, and the first turn where outside-PSNR drops below 25 dB.

Editors are plain callables so real models (Qwen-Image-Layered, Qwen-Image-2.1, relocate(), Kontext, ...) plug in:
    layered_edit(layers: list[RGBA], edit: dict) -> list[RGBA]
    flat_edit(image: RGB, edit: dict) -> RGB
    decompose(image: RGB, n_layers: int) -> list[RGBA]
An edit dict: {"layer": int, "op": "move"|"reprompt"|..., "region": (x0, y0, x1, y1) or None, ...}.
"""
from __future__ import annotations

import json
import math

import numpy as np
from PIL import Image


# ---------------------------------------------------------------- compositing / masks
def composite(layers):
    c = layers[0].convert("RGBA").copy()
    for l in layers[1:]:
        c = Image.alpha_composite(c, l.convert("RGBA"))
    return c.convert("RGB")


def alpha_mask(layer, thr=40):
    return np.asarray(layer.getchannel("A")) > thr


def box_mask(size, box, pad=8):
    m = np.zeros((size[1], size[0]), bool)
    if box is not None:
        x0, y0, x1, y1 = box
        m[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] = True
    return m


# ---------------------------------------------------------------- metrics
def psnr_outside(a, b, edited):
    keep = ~edited
    if keep.sum() == 0:
        return float("nan")
    d = (np.asarray(a, np.float32) - np.asarray(b, np.float32))[keep]
    mse = float((d ** 2).mean())
    return float("inf") if mse == 0 else 10 * math.log10(255 ** 2 / mse)


def ssim_outside(a, b, edited):
    from skimage.metrics import structural_similarity
    _, smap = structural_similarity(np.asarray(a), np.asarray(b), channel_axis=2, data_range=255, full=True)
    keep = ~edited
    return float(smap.mean(axis=2)[keep].mean()) if keep.any() else float("nan")


def lum_shift(a, b):
    return float(np.asarray(b.convert("L"), np.float32).mean() - np.asarray(a.convert("L"), np.float32).mean())


def alpha_iou(l0, l1, thr=40):
    a, b = alpha_mask(l0, thr), alpha_mask(l1, thr)
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def alpha_weighted_l1(l0, l1):
    x, y = np.asarray(l0, np.float32) / 255, np.asarray(l1, np.float32) / 255
    w = np.maximum(x[..., 3], y[..., 3])
    return float((np.abs(x[..., :3] - y[..., :3]).mean(-1) * w).sum() / max(w.sum(), 1e-6))


class Perceptual:
    """Optional LPIPS / DINOv2 similarity on the masked-out image (edited region set to grey in both images)."""

    def __init__(self, lpips_net=None, dino="facebook/dinov2-small"):
        self.lp = None
        try:
            import lpips  # noqa
            self.lp = lpips.LPIPS(net=lpips_net or "alex")
        except Exception:
            pass
        self.dino = None
        if dino:
            try:
                from transformers import AutoImageProcessor, AutoModel
                self.proc, self.dino = AutoImageProcessor.from_pretrained(dino), AutoModel.from_pretrained(dino).eval()
            except Exception:
                pass

    @staticmethod
    def _grey(img, edited):
        x = np.asarray(img).copy(); x[edited] = 128
        return Image.fromarray(x)

    def __call__(self, a, b, edited):
        import torch
        out = {}
        a, b = self._grey(a, edited), self._grey(b, edited)
        if self.lp is not None:
            t = lambda im: torch.from_numpy(np.asarray(im, np.float32) / 127.5 - 1).permute(2, 0, 1)[None]
            with torch.no_grad():
                out["lpips_out"] = float(self.lp(t(a), t(b)))
        if self.dino is not None:
            with torch.no_grad():
                f = [self.dino(**self.proc(images=im, return_tensors="pt")).last_hidden_state[:, 0] for im in (a, b)]
                out["dino_out"] = float(torch.nn.functional.cosine_similarity(f[0], f[1]).item())
        return out


# ---------------------------------------------------------------- runner
def _edit_region(edit, before_layers, after_layers, size):
    """Region an edit is allowed to change: old + new alpha of the edited layer (layered) or the given box."""
    m = box_mask(size, edit.get("region"))
    i = edit.get("layer")
    if i is not None and before_layers is not None and after_layers is not None and i < len(after_layers):
        m |= alpha_mask(before_layers[i]) | alpha_mask(after_layers[i])
    if edit.get("global"):
        m[:] = True                                       # scene-wide story event: nothing is "outside"
    return m


def run_arm(arm, layers0, edits, layered_edit=None, flat_edit=None, decompose=None, perceptual=None):
    """Returns a list of per-turn metric dicts (turn 0 included)."""
    img0 = composite(layers0)
    size = img0.size
    layers, img = [l.copy() for l in layers0], img0
    edited = np.zeros((size[1], size[0]), bool)
    rows = [dict(turn=0, psnr_out=float("inf"), ssim_out=1.0, lum_shift=0.0)]
    for t, e in enumerate(edits, 1):
        before = layers
        if arm == "layered":
            layers = layered_edit(layers, e); img = composite(layers)
        elif arm == "redecompose":
            layers = decompose(composite(layers), len(layers)) if t > 1 else layers
            layers = layered_edit(layers, e); img = composite(layers)
        elif arm == "flat":
            img = flat_edit(img, e); layers = None
        else:
            raise ValueError(arm)
        edited |= _edit_region(e, before, layers, size)
        r = dict(turn=t, psnr_out=psnr_outside(img0, img, edited), ssim_out=ssim_outside(img0, img, edited),
                 lum_shift=lum_shift(img0, img), edited_frac=float(edited.mean()))
        if layers is not None:
            keep = [i for i in range(len(layers0)) if all(ed.get("layer") != i for ed in edits[:t])]
            if keep:
                r["alpha_iou_untouched"] = float(np.mean([alpha_iou(layers0[i], layers[i]) for i in keep]))
                r["alpha_l1_untouched"] = float(np.mean([alpha_weighted_l1(layers0[i], layers[i]) for i in keep]))
        if perceptual is not None:
            r.update(perceptual(img0, img, edited))
        rows.append(r)
    return rows


def summarise(rows, threshold_db=25.0):
    ps = [r["psnr_out"] for r in rows[1:]]
    finite = [min(p, 60.0) for p in ps]                      # cap inf (untouched) at 60 dB for the AUC
    below = next((r["turn"] for r in rows[1:] if r["psnr_out"] < threshold_db), None)
    return dict(turns=len(ps), auc_psnr=float(np.mean(finite)) if finite else None,
                final_psnr=ps[-1] if ps else None, final_ssim=rows[-1]["ssim_out"],
                first_turn_below_threshold=below, threshold_db=threshold_db)


def save(results: dict, path):
    json.dump(results, open(path, "w"), indent=1, default=float)
