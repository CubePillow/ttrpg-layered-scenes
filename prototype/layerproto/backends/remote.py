"""Client for a remote image backend served by layerproto/remote_server.py (Kaggle, Modal, LMU, ...)."""
from __future__ import annotations

import base64
import io
from dataclasses import asdict

import requests
from PIL import Image

from .base import GenParams, ImageBackend


def img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def b64_to_img(s: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(s))).convert("RGBA")


class RemoteBackend(ImageBackend):
    name = "remote"

    def __init__(self, url: str, token: str = "", timeout: float = 600):
        self.url = url.rstrip("/")
        self.headers = {"X-Token": token} if token else {}
        self.timeout = timeout

    def _post(self, route: str, payload: dict) -> Image.Image:
        r = requests.post(f"{self.url}/{route}", json=payload, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return b64_to_img(r.json()["image"])

    def generate_object(self, p: GenParams) -> Image.Image:
        return self._post("generate_object", {"params": asdict(p)})

    def generate_background(self, p: GenParams) -> Image.Image:
        return self._post("generate_background", {"params": asdict(p)})

    def refine_object(self, image: Image.Image, p: GenParams, strength: float) -> Image.Image:
        return self._post("refine_object", {"params": asdict(p), "image": img_to_b64(image), "strength": strength})

    def refine_background(self, image: Image.Image, p: GenParams, strength: float) -> Image.Image:
        return self._post("refine_background", {"params": asdict(p), "image": img_to_b64(image), "strength": strength})

    def info(self) -> dict:
        try:
            return requests.get(f"{self.url}/health", headers=self.headers, timeout=10).json()
        except Exception as e:  # noqa: BLE001
            return {"backend": self.name, "url": self.url, "error": str(e)}
