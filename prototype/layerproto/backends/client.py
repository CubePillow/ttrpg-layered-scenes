"""Client calls to the two GPU servers (layerproto/remote_server.py): generate (SDXL-Turbo) and split (Qwen-Image-2.1 ...).

The connection of each role is looked up at every call (layerproto/connection.py), so a server started after the app is used at
once and a new Kaggle session (new URL and token) needs no restart.
"""
from __future__ import annotations

import requests
from PIL import Image

from .. import connection
from .remote import b64_to_img, img_to_b64

HOW = {"generate": "Start the SDXL-Turbo server (Servers panel, Start) or paste its connection line.",
       "split": "Start the Qwen-Image-2.1 server (Servers panel, Start) or paste its connection line."}


class NotConnected(RuntimeError):
    pass


def _post(role: str, route: str, payload: dict, timeout: float = 900) -> dict:
    c = connection.load(role)
    if not c.configured:
        raise NotConnected(f"Not connected to the {role} server. {HOW[role]}")
    try:
        r = requests.post(f"{c.url}{route}", json=payload, headers={"X-Token": c.token} if c.token else {}, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise NotConnected(f"The {role} server at {c.url} cannot be reached ({type(e).__name__}); it may have stopped (idle) or the "
                           f"Kaggle session ended. {HOW[role]}") from e
    if r.status_code == 401:
        raise NotConnected(f"The {role} server rejected the token (new Kaggle session?). {HOW[role]}")
    if r.status_code == 404:
        raise NotConnected(f"The {role} server has no {route} route; it runs a different profile "
                           f"({connection.load(role).profile or 'unknown'}).")
    if r.status_code >= 400:
        raise RuntimeError(f"{route} failed ({r.status_code}): {r.text[:300]}")
    return r.json()


def txt2img(prompt: str, seed: int = 13, steps: int = 4, size: int = 512, negative: str = "") -> Image.Image:
    return b64_to_img(_post("generate", "/txt2img", dict(prompt=prompt, seed=seed, steps=steps, size=size, negative=negative))["image"]).convert("RGB")


def img2img(image: Image.Image, prompt: str, strength: float = 0.5, seed: int = 13, steps: int = 4, size: int = 512,
            negative: str = "") -> Image.Image:
    return b64_to_img(_post("generate", "/img2img", dict(prompt=prompt, image=img_to_b64(image.convert("RGB")), strength=strength,
                                                         seed=seed, steps=steps, size=size, negative=negative))["image"]).convert("RGB")


def edit_layer(layer: Image.Image, prompt: str, seed: int = 42) -> tuple[Image.Image, dict]:
    """RGBA layer edit on the split server (Qwen-Image-2.1) with the alpha check-and-retry. -> (layer, report)"""
    d = _post("split", "/edit", dict(image=img_to_b64(layer.convert("RGBA")), prompt=prompt, seed=seed), timeout=600)
    return b64_to_img(d["image"]), d.get("report", {})
