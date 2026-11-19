"""Contract for scene-to-layer backends (local LayerDiffuse chain, or the same chain on a remote GPU)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


@dataclass
class ChainParams:
    prompt: str
    seed: int
    width: int = 512
    height: int = 512
    steps: int = 20
    guidance: float = 7.0
    negative_prompt: str = "bad, ugly"


class ChainBackend(ABC):
    name = "chain"

    @abstractmethod
    def background(self, p: ChainParams) -> Image.Image:
        """Opaque base layer from a prompt (RGBA, alpha 255)."""

    @abstractmethod
    def blend(self, scene: Image.Image, p: ChainParams) -> Image.Image:
        """bg2ble: the scene with a new element drawn into it."""

    @abstractmethod
    def extract(self, scene: Image.Image, blended: Image.Image, p: ChainParams) -> Image.Image:
        """bgble2fg: only the new element, as a full-canvas RGBA layer aligned with the scene."""

    def info(self) -> dict:
        return {"backend": self.name}
