"""Story events on a layer stack (gap G2): route one event ("it starts to rain", "night falls", "the forest catches
fire") to per-layer actions, plus procedural effect overlays.

Strategies (research_notes/Layered loop open paths/story_events_global_edits.md):
  (a) recompose  - edit the flat composite with the event prompt, then re-decompose (fallback for geometry changes,
                   e.g. snow piling on objects)
  (b) per_layer  - apply the same instruction to every affected layer (Qwen-Image-2.1 RGBA edit, shared attention)
  (c) bg_relight - edit the background only, then relight the foreground layers against it (IC-Light fbc / LBM),
                   keeping each layer's alpha  <- favoured by the evidence
  (d) effects    - add new effect layers: rain/snow/fog procedurally (below), fire/smoke/glow via LayerDiffuse
                   conditioned on the background
The router returns a plan; executing the generative steps is the job of the backends (Kaggle). The procedural
overlays and colour grading here run on CPU in milliseconds and give an instant preview while the generative pass
runs (ImageDirector, UIST'26: users preferred an immediate proxy over waiting for harmonisation).
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

ACTIONS = ["keep", "relight", "reprompt", "remove"]
EFFECTS = ["rain", "snow", "fog", "night", "fire_glow", "smoke", "none"]

SCHEMA = {
    "type": "object",
    "properties": {
        "strategy": {"type": "string", "enum": ["recompose", "per_layer", "bg_relight", "effects"]},
        "background_prompt": {"type": "string"},
        "layers": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "action": {"type": "string", "enum": ACTIONS},
            "prompt": {"type": "string"}}, "required": ["name", "action", "prompt"]}},
        "effects": {"type": "array", "items": {"type": "string", "enum": EFFECTS}},
        "reason": {"type": "string"},
    },
    "required": ["strategy", "background_prompt", "layers", "effects", "reason"],
}

SYSTEM = """You route a story event to the layers of a 2D scene. The scene is a stack of transparent layers: a background and named objects/characters.
Decide, for the event:
- strategy: "bg_relight" when the event changes weather, light, time of day or atmosphere but not object shapes (most events);
  "per_layer" when several objects themselves change appearance (e.g. "everything freezes", "the toys turn to gold");
  "recompose" only when the event changes geometry across objects (e.g. "snow piles up on everything", "the house collapses");
  "effects" when only an overlay is added and nothing else changes (e.g. "smoke drifts in").
- background_prompt: how the background should look after the event (empty if unchanged).
- for EVERY layer: action "keep" (unchanged; characters keep their identity), "relight" (same object, new lighting/colour from the event),
  "reprompt" (the object itself changes; give the new prompt), or "remove" (it disappears). Keep characters' identity unless the event says otherwise.
- Weather, light and time-of-day changes affect EVERY visible layer: mark trees, props and characters "relight" (not "keep") so they match the new light; "keep" only for layers the event truly does not touch (e.g. indoors).
- A layer may contain several objects (e.g. "campfire and wooden chair"). If only one of them changes or disappears, use "reprompt" with a prompt describing the whole layer after the event (e.g. "extinguished campfire with smoking logs and a wooden chair"), never "remove".
- effects: only overlays physically caused by the event: rain, snow, fog, night, fire_glow, smoke (or none). A colour/material change of one object needs no effect.
Answer with JSON only."""


def route_event(llm, event: str, layer_names: list[str], scene_prompt: str = "") -> dict:
    user = f"Scene: {scene_prompt}\nLayers (back to front): {', '.join(layer_names)}\nEvent: {event}"
    try:
        plan = llm.chat_json(SYSTEM, user, SCHEMA)
    except Exception as e:  # LLM unavailable -> heuristic
        plan = heuristic_route(event, layer_names); plan["reason"] = f"heuristic ({e.__class__.__name__})"
    return normalise_plan(plan, layer_names)


_KW = {"rain": ["rain", "storm", "drizzle", "downpour"], "snow": ["snow", "blizzard", "winter"],
       "fog": ["fog", "mist", "haze"], "night": ["night", "dark", "dusk", "evening", "moon"],
       "fire_glow": ["fire", "burn", "flame", "blaze"], "smoke": ["smoke", "ash"]}


def heuristic_route(event: str, layer_names: list[str]) -> dict:
    e = event.lower()
    eff = [k for k, ws in _KW.items() if any(w in e for w in ws)]
    return {"strategy": "bg_relight" if eff else "per_layer", "background_prompt": event,
            "layers": [{"name": n, "action": "relight" if i else "keep", "prompt": ""} for i, n in enumerate(layer_names)],
            "effects": eff or ["none"], "reason": "keyword heuristic"}


def normalise_plan(plan: dict, layer_names: list[str]) -> dict:
    by = {d.get("name", "").strip().lower(): d for d in plan.get("layers", []) if isinstance(d, dict)}
    plan["layers"] = [{"name": n, "action": (by.get(n.lower(), {}).get("action") or "keep"),
                       "prompt": by.get(n.lower(), {}).get("prompt", "")} for n in layer_names]
    for d in plan["layers"]:
        if d["action"] not in ACTIONS:
            d["action"] = "keep"
    plan["effects"] = [x for x in plan.get("effects", []) if x in EFFECTS and x != "none"]
    if plan.get("strategy") not in SCHEMA["properties"]["strategy"]["enum"]:
        plan["strategy"] = "bg_relight"
    return plan


# ---------------------------------------------------------------- CPU preview: grading + procedural overlays
def grade(img: Image.Image, effect: str, strength: float = 1.0) -> Image.Image:
    """Cheap colour grade for a layer (keeps alpha). Instant preview of 'relight' before IC-Light runs."""
    x = np.asarray(img.convert("RGBA"), np.float32)
    rgb, a = x[..., :3], x[..., 3:]
    if effect == "night":
        lum = rgb.mean(-1, keepdims=True)
        rgb = (0.35 * rgb + 0.25 * lum) * np.array([0.75, 0.85, 1.25])
    elif effect == "rain":
        rgb = rgb * 0.8 + rgb.mean(-1, keepdims=True) * 0.15 * np.array([0.9, 1.0, 1.1])
    elif effect == "snow":
        rgb = rgb * 0.85 + 40 * np.array([0.95, 1.0, 1.1])
    elif effect == "fog":
        rgb = rgb * 0.7 + 0.3 * 200
    elif effect == "fire_glow":
        rgb = rgb * np.array([1.2, 0.95, 0.7]) + np.array([30, 8, 0])
    t = strength
    out = (1 - t) * x[..., :3] + t * rgb
    return Image.fromarray(np.concatenate([np.clip(out, 0, 255), a], -1).astype(np.uint8), "RGBA")


def overlay(size, effect: str, seed: int = 0, density: float = 1.0) -> Image.Image | None:
    """Procedural RGBA effect layer (rain streaks, snow flakes, fog gradient, fire glow, smoke)."""
    W, H = size
    rng = np.random.default_rng(seed)
    lay = np.zeros((H, W, 4), np.float32)
    if effect == "rain":
        n = int(W * H / 900 * density)
        xs, ys = rng.integers(0, W, n), rng.integers(0, H, n)
        L = rng.integers(14, 30, n)
        for x, y, l in zip(xs, ys, L):
            for k in range(l):
                yy, xx = y + k, x + k // 4
                if 0 <= yy < H and 0 <= xx < W:
                    lay[yy, xx:xx + 2] = (215, 225, 240, 170)
        img = Image.fromarray(lay.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.5))
        return img
    if effect == "snow":
        n = int(W * H / 700 * density)
        xs, ys, r = rng.integers(0, W, n), rng.integers(0, H, n), rng.integers(1, 3, n)
        for x, y, rr in zip(xs, ys, r):
            lay[max(0, y - rr):y + rr, max(0, x - rr):x + rr] = (250, 250, 255, 220)
        return Image.fromarray(lay.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(0.8))
    if effect == "fog":
        noise = rng.random((H // 32 + 2, W // 32 + 2))
        n = np.asarray(Image.fromarray((noise * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
        ramp = np.linspace(0.25, 0.75, H)[:, None]                # denser near the ground
        lay[..., :3] = 215; lay[..., 3] = 255 * np.clip(0.5 * ramp + 0.4 * n * ramp, 0, 0.8) * density
        return Image.fromarray(lay.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(6))
    if effect == "fire_glow":
        yy = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
        lay[..., :3] = (255, 120, 30); lay[..., 3] = 90 * yy ** 2 * density
        return Image.fromarray(lay.astype(np.uint8), "RGBA")
    if effect == "smoke":
        noise = rng.random((H // 48 + 2, W // 48 + 2))
        n = np.asarray(Image.fromarray((noise * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
        ramp = np.linspace(0.8, 0.1, H)[:, None]
        lay[..., :3] = 90; lay[..., 3] = 255 * np.clip(n * ramp * 0.7, 0, 0.7) * density
        return Image.fromarray(lay.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(10))
    return None


def preview(layers: list[Image.Image], plan: dict, seed: int = 0) -> Image.Image:
    """Instant CPU preview of a plan: grade relit layers, drop removed ones, add procedural overlays."""
    eff = plan["effects"]
    g = eff[0] if eff else None
    out = []
    for i, (l, d) in enumerate(zip(layers, plan["layers"])):
        if d["action"] == "remove":
            continue
        if g and (g in ("night", "rain", "snow", "fog") or d["action"] in ("relight", "reprompt")):
            l = grade(l, g)
        out.append(l)
    c = out[0].convert("RGBA")
    for l in out[1:]:
        c = Image.alpha_composite(c, l.convert("RGBA"))
    for e in eff:
        o = overlay(c.size, e, seed)
        if o is not None:
            c = Image.alpha_composite(c, o)
    return c.convert("RGB")
