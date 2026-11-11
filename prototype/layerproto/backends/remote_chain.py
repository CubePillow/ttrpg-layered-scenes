"""Client for the scene-to-layer chain running on a remote GPU (Kaggle / Modal) via layerproto/remote_server.py."""
from __future__ import annotations

from dataclasses import asdict

import requests
from PIL import Image

from .chain_base import ChainBackend, ChainParams
from .remote import b64_to_img, img_to_b64


class RemoteChain(ChainBackend):
    name = "remote-chain"

    def __init__(self, url: str, token: str = "", timeout: float = 900):
        self.url = url.rstrip("/")
        self.headers = {"X-Token": token} if token else {}
        self.timeout = timeout

    def _post(self, route: str, payload: dict) -> Image.Image:
        r = requests.post(f"{self.url}/{route}", json=payload, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return b64_to_img(r.json()["image"])

    def background(self, p: ChainParams) -> Image.Image:
        return self._post("chain/background", {"params": asdict(p)})

    def blend(self, scene: Image.Image, p: ChainParams) -> Image.Image:
        return self._post("chain/blend", {"params": asdict(p), "scene": img_to_b64(scene)})

    def extract(self, scene: Image.Image, blended: Image.Image, p: ChainParams) -> Image.Image:
        return self._post("chain/extract", {"params": asdict(p), "scene": img_to_b64(scene),
                                            "blended": img_to_b64(blended)})

    def relocate(self, scene: Image.Image, layer: Image.Image, box, prompt: str, seed: int, strength: float = 0.5,
                 pin_frac: float = 0.4, w: int = 512, h: int = 512, steps: int = 20, guidance: float = 7.0,
                 negative: str = "bad, ugly", **_ignored):
        """Same contract as LayerDiffuseChain.relocate: returns (naive composite, harmonised composite, new layer)."""
        p = ChainParams(prompt=prompt, seed=seed, width=w, height=h, steps=steps, guidance=guidance, negative_prompt=negative)
        r = requests.post(f"{self.url}/chain/relocate", headers=self.headers, timeout=self.timeout,
                          json={"params": asdict(p), "scene": img_to_b64(scene.convert("RGB")), "layer": img_to_b64(layer),
                                "box": [int(v) for v in box], "strength": strength, "pin_frac": pin_frac})
        r.raise_for_status()
        j = r.json()
        return None, b64_to_img(j["composite"]), b64_to_img(j["layer"])

    def info(self) -> dict:
        try:
            return requests.get(f"{self.url}/health", headers=self.headers, timeout=15).json()
        except Exception as e:  # noqa: BLE001
            return {"backend": self.name, "url": self.url, "error": str(e)}
