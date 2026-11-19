"""Image -> layers with Qwen-Image-2.1 RGBA extraction (one edit call per object) for the /decompose route.

Measured on fox & cottage (docs/models/qwen-image-2.1.md, T4 x2, 512 px, about 23-27 s per call): "Extract only the X ...
without the Y in front" returns a whole, hole-free object as RGBA, and "Remove X and fill in what was behind it" gives the
background. Objects are extracted from the ORIGINAL image, each with the others named as exclusions.

    dec = Qwen21Decomposer(pipe)              # pipe: a loaded QwenImage21Pipeline (see tools/make_qwen21_extract_trial.py)
    layers = dec(image, DecomposeParams(names=["cottage", "big tree", "red fox"], method="qwen21-extract"))
    # background first, then one full-canvas RGBA per name, in the given order (back to front)
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from ..layer_edit import edit_layer_keep_alpha
from .decomposer import DecomposeParams

RGBA = "This is an RGBA image with transparency. {}. The image has alpha channel and the background is transparent."


def extract_prompt(name: str, others: list[str]) -> str:
    excl = (", without the " + ", ".join(others) + " in front of it") if others else ""
    return RGBA.format(f"Extract only the {name} as a complete object{excl}")


def background_prompt(names: list[str]) -> str:
    return f"Remove the {', the '.join(names)} from the scene and fill in what was behind them, keep everything else exactly the same"


class Qwen21Decomposer:
    def __init__(self, pipe, size: int = 512, seeds=(42, 7, 123, 2024)):
        self.pipe, self.size, self.seeds = pipe, size, seeds

    def _run(self, image: Image.Image, prompt: str, seed: int) -> Image.Image:
        import torch
        with torch.inference_mode():
            return self.pipe(prompt=prompt, image=[image], width=self.size, height=self.size, output_resolution=self.size,
                             use_kv_cache=True, generator=torch.Generator(self.pipe._execution_device).manual_seed(seed)).images[0]

    def __call__(self, image: Image.Image, p: DecomposeParams) -> list[Image.Image]:
        im = image.convert("RGB")
        small = im.resize((self.size, self.size), Image.LANCZOS)
        names = list(p.names)
        seeds = tuple(sd + int(p.seed) for sd in self.seeds)             # p.seed 0 = the measured defaults; other values give other versions
        if not names:
            raise ValueError("qwen21-extract needs names (one per object)")
        layers = []
        if p.only in (-1, 0):
            bg = self._run(small, background_prompt(names), seeds[0]).convert("RGB")
            layers.append(bg.resize(im.size, Image.LANCZOS).convert("RGBA"))
        for i, n in enumerate(names):
            if p.only >= 0 and i != p.only - 1:
                continue
            others = [m for j, m in enumerate(names) if j > i]           # objects drawn in front of this one
            ref = None
            if p.boxes and i < len(p.boxes):                             # a box tells which share of the canvas the object should keep
                x0, y0, x1, y1 = p.boxes[i]
                ref = np.zeros((im.size[1], im.size[0]), bool)
                ref[int(y0):int(y1), int(x0):int(x1)] = True
            out = None
            for seed in seeds:
                cand = self._run(small, extract_prompt(n, others), seed).convert("RGBA")
                a = np.asarray(cand.getchannel("A"))
                if (a > 16).mean() > 0.002 and (a > 16).mean() < 0.9:    # not empty, not a flooded scene
                    out = cand
                    break
                out = out or cand
            layers.append(out.resize(im.size, Image.LANCZOS))
        return layers
