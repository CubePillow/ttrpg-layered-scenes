"""Profile `sam2`: Grounding DINO (tiny) + SAM2 (hiera-small) + LaMa, with optional SDXL-inpaint amodal fill; method `sam2-lama` on /decompose.

Loads in about 45 s; 5-12 s per image. The first request with `amodal=True` also loads SDXL-inpaint (about 75 s, once).
"""
from __future__ import annotations

PIP = ["git+https://github.com/facebookresearch/sam2.git", "--no-deps simple-lama-inpainting", "fire", "diffusers==0.37.0"]


def make(log=print):
    from ..backends.decomposer import MethodRouter
    from ..backends.sam2_decomposer import Sam2Decomposer
    return MethodRouter({"sam2-lama": Sam2Decomposer(device="cuda")})
