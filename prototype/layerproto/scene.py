"""Scene / layer data model, stored as scenes/<id>/scene.json plus one PNG per layer variant."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

from PIL import Image


@dataclass
class Variant:
    file: str  # path relative to the scene folder
    seed: int
    prompt: str
    mode: str = "new"  # new | refine | sketch
    caption: str = ""
    matched_words: list = field(default_factory=list)
    missing_words: list = field(default_factory=list)
    seconds: float = 0.0
    transparent_pct: float = 0.0  # share of fully transparent pixels; ~0 on an element layer = failed extraction
    blend: str = ""      # the scene with this element drawn in (bg2ble output), relative to the scene folder
    scene_in: str = ""   # the scene it was generated into (composite of the layers below at that time)


@dataclass
class Layer:
    id: str
    name: str
    role: str  # background | object (an element generated into the scene)
    depth: int  # 0 = furthest back
    prompt: str
    adjectives: list = field(default_factory=list)
    box: list = field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])  # x, y, w, h (0..1): LLM layout hint, unused
    # canvas transform applied when composing (Photoshop-style move / resize); identity = as generated
    dx: float = 0.0     # horizontal shift, fraction of canvas width
    dy: float = 0.0     # vertical shift, fraction of canvas height
    scale: float = 1.0  # around the layer's visible centre
    rot: float = 0.0    # degrees, counter-clockwise, around the layer's visible centre
    variants: list = field(default_factory=list)  # list[Variant]
    selected: int = 0
    enabled: bool = True  # False = skipped by "generate all"

    def current(self) -> Optional[Variant]:
        if not self.variants:
            return None
        return self.variants[min(self.selected, len(self.variants) - 1)]


@dataclass
class Scene:
    id: str
    user_input: str
    refined_prompt: str = ""
    style: str = ""
    layers: list = field(default_factory=list)  # list[Layer]
    relations: list = field(default_factory=list)  # [{"subject","relation","object"}]
    words: list = field(default_factory=list)  # [{"word","type","layer"}]
    split_mode: str = "objects"  # objects | bands | exact
    n_layers: int = 6
    created: float = field(default_factory=time.time)

    # ---- helpers -------------------------------------------------------------
    def layer(self, layer_id: str) -> Layer:
        for l in self.layers:
            if l.id == layer_id:
                return l
        raise KeyError(layer_id)

    def folder(self, scenes_dir: str) -> str:
        p = os.path.join(scenes_dir, self.id)
        os.makedirs(p, exist_ok=True)
        return p

    def save_image(self, scenes_dir: str, layer: Layer, img: Image.Image, tag: str) -> str:
        rel = f"{layer.id}__{tag}.png"
        img.save(os.path.join(self.folder(scenes_dir), rel))
        return rel

    def save(self, scenes_dir: str) -> str:
        path = os.path.join(self.folder(scenes_dir), "scene.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        return path

    @staticmethod
    def load(path: str) -> "Scene":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        layers = []
        for ld in d.pop("layers", []):
            vs = [Variant(**v) for v in ld.pop("variants", [])]
            layers.append(Layer(variants=vs, **ld))
        return Scene(layers=layers, **d)


def slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:24] or "layer"


def new_scene_id(text: str) -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + slug(text)[:16] + "-" + uuid.uuid4().hex[:4]
