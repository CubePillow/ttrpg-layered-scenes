"""Procedural cast-shadow layer for an RGBA object layer (CPU, milliseconds).

Recipe after EasyOmnimatte (CVPR 2026, supplement): squash the object's alpha vertically, shear it along the light
direction, make it semi-transparent and blur it more with distance from the contact line; plus a small
ambient-occlusion blob where the object touches the ground. Output is a black RGBA layer that sits between the
background and the object and moves with the object (DreamLayer's IRH also puts shadows in the layer below).

    from layerproto.shadow import shadow_layer
    sh = shadow_layer(obj_rgba, light_dx=0.6, squash=0.35, opacity=0.55)
    scene = Image.alpha_composite(Image.alpha_composite(bg, sh), obj_rgba)
"""
import numpy as np
from PIL import Image, ImageFilter


def _bbox(a, thr=40):
    ys, xs = np.nonzero(a > thr)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max()


def shadow_layer(obj: Image.Image, per_component: bool = True, min_area: float = 0.002, background: Image.Image | None = None,
                 multiply: float = 0.3, **kw) -> Image.Image:
    """Shadow layer; with `background` (the RGB picture below the object) the shadow is a multiply-style shadow: its colour is the
    ground colour times `multiply` (darker for smaller values) instead of flat black, so it keeps the ground's hue and texture
    (cobblestones show through) and does not look like a black sticker on a coloured meadow. Same alpha as the black version."""
    lay = _shadow_layer(obj, per_component=per_component, min_area=min_area, **kw)
    if background is not None:
        rgb = np.asarray(background.convert("RGB").resize(lay.size), np.float32) * multiply
        a = lay.getchannel("A")
        lay = Image.fromarray(np.dstack([rgb.clip(0, 255).astype(np.uint8), np.asarray(a)]), "RGBA")
    return lay


def _shadow_layer(obj: Image.Image, per_component: bool = True, min_area: float = 0.002, **kw) -> Image.Image:
    """Shadow for every separate object in the layer (Qwen sometimes groups several objects into one layer, each
    needs its own contact line). Components smaller than min_area of the canvas are ignored."""
    if not per_component:
        return _shadow_single(obj, **kw)
    from scipy import ndimage
    a = np.asarray(obj.getchannel("A"))
    lab, n = ndimage.label(ndimage.binary_dilation(a > kw.get("alpha_thr", 40), iterations=3))
    acc = np.zeros(a.shape, np.float32)
    for i in range(1, n + 1):
        m = lab == i
        if m.mean() < min_area:
            continue
        part = obj.copy(); part.putalpha(Image.fromarray(np.where(m, a, 0).astype(np.uint8)))
        acc = np.maximum(acc, np.asarray(_shadow_single(part, **kw).getchannel("A"), np.float32))
    acc *= 1 - a / 255.0
    lay = Image.new("RGBA", obj.size, (0, 0, 0, 0)); lay.putalpha(Image.fromarray(acc.astype(np.uint8)))
    return lay


def _shadow_single(obj: Image.Image, light_dx: float = 0.6, squash: float = 0.35, opacity: float = 0.55,
                 blur_near: float = 2.0, blur_far: float = 10.0, ao: float = 0.35, contact_y: int | None = None,
                 alpha_thr: int = 40, max_len: float = 0.12) -> Image.Image:
    """max_len: cap on shadow length as a fraction of canvas height (keeps tall objects' shadows on the ground plane
    instead of climbing the background). obj: RGBA layer (full canvas). light_dx: horizontal shear of the shadow per unit height (+ = light from the
    left, shadow falls right). squash: shadow height as a fraction of object height. contact_y: ground line in
    pixels (default: bottom of the object's alpha). Returns an RGBA layer of the same size (black, alpha = shadow)."""
    W, H = obj.size
    a = np.asarray(obj.getchannel("A"), dtype=np.float32)
    bb = _bbox(a, alpha_thr)
    if bb is None:
        return Image.new("RGBA", obj.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = bb
    base = y1 if contact_y is None else contact_y
    h = max(1, base - y0)
    # each shadow row r (0 = contact line, going up) samples object row base - r/squash, shifted by shear
    sh_h = max(1, min(int(h * squash), int(max_len * H)))
    squash = sh_h / h                                              # keep full object height mapped onto the capped shadow
    out = np.zeros((H, W), np.float32)
    dist = np.zeros((H, W), np.float32)
    xs = np.arange(W)
    for r in range(sh_h):
        src_y = int(round(base - r / squash))
        dst_y = base - r
        if src_y < 0 or dst_y < 0 or dst_y >= H:
            continue
        shift = int(round(light_dx * r / squash))
        src_x = xs - shift
        ok = (src_x >= 0) & (src_x < W)
        out[dst_y, ok] = a[src_y, src_x[ok]] / 255.0
        dist[dst_y, :] = r / sh_h
    # distance-dependent blur: blend a near (sharp) and far (soft) blur by row distance
    im = Image.fromarray((out * 255).astype(np.uint8))
    near = np.asarray(im.filter(ImageFilter.GaussianBlur(blur_near)), np.float32) / 255
    far = np.asarray(im.filter(ImageFilter.GaussianBlur(blur_far)), np.float32) / 255
    soft = near * (1 - dist) + far * dist
    soft *= (1 - 0.6 * dist)                                     # fades with distance from contact
    # contact ambient occlusion: flat ellipse under the footprint
    foot = a[max(0, base - 3):base + 1].max(axis=0) > alpha_thr
    if foot.any():
        fx = np.nonzero(foot)[0]
        cx, rx = (fx.min() + fx.max()) / 2, max(4, (fx.max() - fx.min()) / 2 * 1.1)
        ry = max(2, rx * 0.12)
        yy, xx = np.mgrid[0:H, 0:W]
        blob = np.clip(1 - ((xx - cx) / rx) ** 2 - ((yy - base) / ry) ** 2, 0, 1)
        blob = np.asarray(Image.fromarray((blob * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(ry)),
                          np.float32) / 255
        soft = np.maximum(soft * opacity, blob * ao)
    else:
        soft = soft * opacity
    soft *= 1 - a / 255.0                                         # never darken the object itself
    alpha = (np.clip(soft, 0, 1) * 255).astype(np.uint8)
    lay = Image.new("RGBA", obj.size, (0, 0, 0, 0))
    lay.putalpha(Image.fromarray(alpha))
    return lay
