"""Apply a routed story event (events.route_event plan) to a stack of RGBA layers with a pluggable layer editor.

Ties together the three measured pieces: the plan (events.py), the alpha-keeping retry (layer_edit.py) and the procedural
shadow layer (shadow.py). Pure CPU glue: the editor is any callable, so the real one (Qwen-Image-2.1 RGBA edit on a GPU
server) and a stub for tests plug in the same way.

    editor(layer_rgba, prompt, seed) -> edited layer (RGBA)
    out, report = apply_event(layers, plan, editor)      # layers: background first, parallel to plan["layers"]

Per layer: keep -> unchanged; relight / reprompt -> edit_layer_keep_alpha with the layer's prompt (falls back to a colour
grade for relight, or the unedited layer for reprompt, if no seed keeps the transparency); remove -> dropped.
Effects of the plan are drawn as procedural overlays on top; every object layer gets a cast-shadow layer underneath it.
"""
from __future__ import annotations

from typing import Callable

from PIL import Image

from . import events as E
from .layer_edit import edit_layer_keep_alpha
from .shadow import shadow_layer

RELIGHT = ("Relight this object for this event: {event}. Keep its exact shape, pose and painting style")
RGBA = "This is an RGBA image with transparency. {}. The image has alpha channel and the background is transparent."


def layer_prompt(d: dict, event: str) -> str:
    base = d["prompt"] or RELIGHT.format(event=event)
    return RGBA.format(base)


def apply_event(layers: list[Image.Image], plan: dict, editor: Callable[[Image.Image, str, int], Image.Image],
                event: str = "", seeds=(42, 7, 123, 2024), shadows: bool = True, overlay_effects: bool = True,
                seed: int = 0) -> tuple[list[Image.Image], list[dict]]:
    """Returns (new layers back to front, per-layer report). Shadow and overlay layers are included in the list."""
    event = event or plan.get("background_prompt", "")
    eff = plan.get("effects", [])
    out: list[Image.Image] = []
    report: list[dict] = []
    for i, (layer, d) in enumerate(zip(layers, plan["layers"])):
        act = d["action"]
        rep = {"name": d["name"], "action": act}
        if act == "remove":
            report.append(rep)
            continue
        new = layer.convert("RGBA")
        if act in ("relight", "reprompt"):
            prompt = layer_prompt(d, event)
            new, r = edit_layer_keep_alpha(lambda img, s: editor(img, prompt, s), new, seeds=seeds)
            rep.update(r)
            if not r["accepted"]:
                if act == "relight" and eff:
                    new = E.grade(layer.convert("RGBA"), eff[0])
                    rep["fallback"] = f"grade:{eff[0]}"
                else:
                    new = layer.convert("RGBA")
                    rep["fallback"] = "unedited"
        report.append(rep)
        if shadows and i > 0:
            below = out[0].copy()                               # the picture below this object: the shadow takes its colour (multiply)
            for L in out[1:]:
                below.alpha_composite(L.convert("RGBA"))
            sh = shadow_layer(new, background=below.convert("RGB"))
            if sh.getchannel("A").getbbox() is not None:
                out.append(sh)
                rep["shadow"] = True
        out.append(new)
    if overlay_effects:
        for e in eff:
            o = E.overlay(out[0].size, e, seed)
            if o is not None:
                out.append(o)
    return out, report
