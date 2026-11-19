"""Profile `studio`: SDXL-Turbo and Qwen-Image-2.1 in ONE Kaggle session (one Start, one idle clock, one session of quota).

Memory plan on the two T4s (15 GiB each), measured for each model alone: Qwen-Image-2.1 about 21 GiB (8.0 + 12.7), SDXL-Turbo 7.5 GiB peak.
  * Qwen-Image-2.1 stays resident, but only 2.5 GiB of its 16.3 GiB text encoder goes to GPU 0 (the rest to GPU 1), so GPU 0 holds the
    transformer, the VAE and a small slice, about 6 GiB, and keeps roughly 8 GiB free.
  * SDXL-Turbo stays in CPU memory and visits GPU 0 part by part (text encoders, UNet, VAE) only while a picture is made: peak about 5.5 GiB.
    A picture takes a few seconds longer than the 1.5 s of the dedicated session (CPU to GPU copy of the 5 GiB UNet per call).
/health reports the free GiB per GPU (`gpu_free_gib`) so the fit can be checked on a live session. Routes: /txt2img, /img2img, /decompose, /edit.
"""
from __future__ import annotations

import time

from . import qwen21, sdxl_turbo


def make(log=print):
    t0 = time.time()
    dec = qwen21.make(log, te_gpu0="2.5GiB")          # the MethodRouter with .editor
    log(f"qwen-image-2.1 ready {time.time() - t0:.0f} s")
    dec.generator = sdxl_turbo.make(log, offload=True)
    log(f"studio ready {time.time() - t0:.0f} s")
    return dec
