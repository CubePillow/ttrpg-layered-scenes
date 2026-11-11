"""Image backend contract. Every backend returns RGBA PIL images.

Swap the local CPU backend for a remote GPU one (Kaggle, Modal, ...) without touching the app:
the remote server (layerproto/remote_server.py) exposes exactly these calls over HTTP.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PIL import Image


@dataclass
class GenParams:
    prompt: str
    seed: int
    width: int = 512
    height: int = 512
    steps: int = 4
    guidance: float = 1.0
    negative_prompt: str = ""


class ImageBackend(ABC):
    name = "base"

    @abstractmethod
    def generate_object(self, p: GenParams) -> Image.Image:
        """Transparent RGBA object layer from a prompt."""

    @abstractmethod
    def generate_background(self, p: GenParams) -> Image.Image:
        """Opaque full-frame background layer (returned as RGBA, alpha=255)."""

    @abstractmethod
    def refine_object(self, image: Image.Image, p: GenParams, strength: float) -> Image.Image:
        """img2img on an existing RGBA object layer (or a sketch turned into RGBA); keeps transparency."""

    @abstractmethod
    def refine_background(self, image: Image.Image, p: GenParams, strength: float) -> Image.Image:
        """img2img on an opaque background layer."""

    def info(self) -> dict:
        return {"backend": self.name}


def effective_steps(steps: int, strength: float) -> int:
    """Turbo img2img runs int(steps*strength) steps; make sure at least one actually runs."""
    import math

    strength = max(0.05, min(1.0, strength))
    return max(steps, math.ceil(1.0 / strength))


def sketch_to_rgba(img: Image.Image, white_threshold: int = 235) -> Image.Image:
    """Treat near-white paper as transparent so a hand sketch can seed an object layer."""
    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and r >= white_threshold and g >= white_threshold and b >= white_threshold:
                px[x, y] = (r, g, b, 0)
    return rgba


def opaque(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    rgba.putalpha(255)
    return rgba


def placeholder(p: GenParams, transparent: bool) -> Optional[Image.Image]:  # pragma: no cover - debug helper
    from PIL import ImageDraw

    img = Image.new("RGBA", (p.width, p.height), (0, 0, 0, 0) if transparent else (90, 110, 140, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([p.width * 0.25, p.height * 0.25, p.width * 0.75, p.height * 0.75], fill=(220, 160, 60, 255))
    d.text((10, 10), p.prompt[:60], fill=(255, 255, 255, 255))
    return img
