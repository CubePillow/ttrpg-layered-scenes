"""Profile `sdxl-turbo`: the fast first step (text to image, image to image) as its own Kaggle session.

It runs next to the `qwen21` session instead of inside it: both fit a T4 pair alone, they rarely generate at the same time, and Kaggle
allows two GPU sessions at once. About 7.5 GiB on one T4; 1.1-1.5 s per 512 px image (docs/models/sdxl-turbo.md).

    gen = make()                          # a Generator; build_app(None, token, generator=gen, profile="sdxl-turbo")
    gen.txt2img("a red fox ...", seed=13, steps=4, size=512)
    gen.img2img(image, "at night", strength=0.5, ...)      # regenerates the picture; it does not preserve the content

The weights come from the attached `weights-sdxl-turbo` notebook output when there is one, else from Hugging Face (about 7 GB).
Stability AI's licence for the Turbo models applies (non-commercial use here).
"""
from __future__ import annotations

import glob
import os
import shutil
import time

REPO = "stabilityai/sdxl-turbo"
WEIGHTS_KERNEL = "weights-sdxl-turbo"
PIP = ["diffusers==0.37.0", "transformers>=4.51", "accelerate"]


def find_weights(log=print) -> str:
    hit = glob.glob("/kaggle/input/**/sdxl-turbo/model_index.json", recursive=True)
    if hit:
        log("weights from the attached Kaggle input (no download); copying to local disk (reading tensors from the mount took 416 s)")
        return shutil.copytree(os.path.dirname(hit[0]), "/tmp/sdxl-turbo", dirs_exist_ok=True)
    log("weights input not attached: downloading from Hugging Face")
    return REPO


class Generator:
    def __init__(self, log=print, offload: bool = False):
        """offload=True: the weights stay in CPU memory and each part (text encoders, UNet, VAE) visits GPU 0 only while it runs
        (diffusers model offload, peak about 5.5 GiB instead of 7.5): needed when Qwen-Image-2.1 shares the GPUs (profile studio)."""
        import torch
        from diffusers import AutoPipelineForImage2Image, AutoPipelineForText2Image

        t0 = time.time()
        src = find_weights(log)
        self.torch = torch
        self.t2i = AutoPipelineForText2Image.from_pretrained(src, torch_dtype=torch.float16, variant="fp16")
        if offload:
            self.t2i.enable_model_cpu_offload(gpu_id=0)
        else:
            self.t2i.to("cuda:0")
        self.i2i = AutoPipelineForImage2Image.from_pipe(self.t2i)               # shares the weights (and their offload hooks)
        self.t2i.set_progress_bar_config(disable=True)
        self.i2i.set_progress_bar_config(disable=True)
        log(f"loaded {time.time() - t0:.0f} s")
        self.txt2img("warm-up", 1, 1, 512, "")                                    # first call compiles kernels

    def txt2img(self, prompt: str, seed: int = 13, steps: int = 4, size: int = 512, negative: str = ""):
        g = self.torch.Generator("cuda:0").manual_seed(int(seed))
        with self.torch.inference_mode():
            return self.t2i(prompt=prompt, num_inference_steps=int(steps), guidance_scale=0.0, width=int(size), height=int(size),
                            generator=g).images[0]

    def img2img(self, image, prompt: str, strength: float = 0.75, seed: int = 13, steps: int = 4, size: int = 512, negative: str = ""):
        g = self.torch.Generator("cuda:0").manual_seed(int(seed))
        steps = max(int(steps), int(1 / max(float(strength), 0.05)) + 1)          # strength x steps must be at least 1
        with self.torch.inference_mode():
            return self.i2i(prompt=prompt, image=image.convert("RGB").resize((int(size), int(size))), strength=float(strength),
                            num_inference_steps=steps, guidance_scale=0.0, generator=g).images[0]


def make(log=print, offload: bool = False) -> Generator:
    return Generator(log, offload)
