"""SDXL(-Turbo) + LayerDiffuse transparent generation.

Runs on CPU (float32) locally, or on CUDA (float16) on Kaggle/Modal through remote_server.py.
Uses the MIT diffusers port vendored at prototype/vendor/diffuser_layerdiffuse:
  - LoRA  rootonchair/diffuser_layerdiffuse / diffuser_layer_xl_transparent_attn.safetensors
  - alpha decoder / encoder  LayerDiffusion/layerdiffusion-v1 (CreativeML OpenRAIL-M)
Backgrounds are generated with the LoRA disabled and the plain (opaque) decode path.
"""
from __future__ import annotations

import os
import sys
import threading
import time

from PIL import Image

from .base import GenParams, ImageBackend, effective_steps, opaque

_VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "vendor", "diffuser_layerdiffuse")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

LORA_REPO = "rootonchair/diffuser_layerdiffuse"
LORA_FILE = "diffuser_layer_xl_transparent_attn.safetensors"
LD_REPO = "LayerDiffusion/layerdiffusion-v1"
DECODER_FILE = "vae_transparent_decoder.safetensors"
ENCODER_FILE = "vae_transparent_encoder.safetensors"


class LayerDiffuseSDXL(ImageBackend):
    name = "layerdiffuse-sdxl"

    def __init__(self, model: str = "stabilityai/sdxl-turbo", device: str = "auto", alpha_quality: str = "fast",
                 cpu_offload: bool = False):
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        self.model = model
        self.alpha_quality = alpha_quality
        self.cpu_offload = cpu_offload
        self._device_pref = device
        self._lock = threading.Lock()
        self._pipe = None
        self._img2img = None
        self._encoder = None
        self.load_seconds = 0.0

    # ---- loading ---------------------------------------------------------------
    def _load(self):
        if self._pipe is not None:
            return
        import torch
        from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        from layer_diffuse.models import TransparentVAEDecoder, TransparentVAEEncoder

        t0 = time.time()
        dev = self._device_pref
        if dev == "auto":
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if dev == "cuda" else torch.float32
        self.device, self.dtype = dev, dtype

        vae = TransparentVAEDecoder.from_pretrained(self.model, subfolder="vae", torch_dtype=dtype)
        if dtype == torch.float16:
            vae.config.force_upcast = False
        vae.set_transparent_decoder(load_file(hf_hub_download(LD_REPO, DECODER_FILE)))
        if self.alpha_quality == "fast":
            # one decoder pass instead of the 8-way flip/rotate median: ~8x cheaper, slightly noisier edges
            vae.estimate_augmented = lambda pixel, latent: vae.estimate_single_pass(pixel, latent).clip(0, 1)
        self._vae = vae

        pipe = StableDiffusionXLPipeline.from_pretrained(self.model, vae=vae, torch_dtype=dtype, add_watermarker=False)
        pipe.load_lora_weights(LORA_REPO, weight_name=LORA_FILE, adapter_name="layerdiffuse")
        if self.cpu_offload and dev == "cuda":
            pipe.enable_model_cpu_offload()
        else:
            pipe = pipe.to(dev)
        # make sure every component shares one dtype on CPU (same fix as the local fastsdcpu patch)
        if dev == "cpu":
            for comp in pipe.components.values():
                if hasattr(comp, "to") and hasattr(comp, "parameters"):
                    comp.to(dtype=dtype)
        self._pipe = pipe
        self._img2img = StableDiffusionXLImg2ImgPipeline(**pipe.components)
        self._encoder = TransparentVAEEncoder(load_file(hf_hub_download(LD_REPO, ENCODER_FILE)), device=dev, torch_dtype=dtype)
        self.load_seconds = time.time() - t0

    # ---- mode switches -----------------------------------------------------------
    def _transparent(self, on: bool):
        if on:
            self._pipe.enable_lora()
            self._vae.mod_number = 1
        else:
            self._pipe.disable_lora()
            self._vae.mod_number = None  # plain decode -> opaque RGB with alpha 1

    def _gen(self, seed):
        import torch

        return torch.Generator("cpu").manual_seed(int(seed))

    # ---- API ---------------------------------------------------------------------
    def generate_object(self, p: GenParams) -> Image.Image:
        with self._lock:
            self._load()
            self._transparent(True)
            img = self._pipe(prompt=p.prompt, negative_prompt=p.negative_prompt or None, num_inference_steps=p.steps,
                             guidance_scale=p.guidance, width=p.width, height=p.height,
                             generator=self._gen(p.seed), return_dict=False)[0][0]
            return img.convert("RGBA")

    def generate_background(self, p: GenParams) -> Image.Image:
        with self._lock:
            self._load()
            self._transparent(False)
            try:
                img = self._pipe(prompt=p.prompt, negative_prompt=p.negative_prompt or None, num_inference_steps=p.steps,
                                 guidance_scale=p.guidance, width=p.width, height=p.height,
                                 generator=self._gen(p.seed), return_dict=False)[0][0]
            finally:
                self._transparent(True)
            return opaque(img)

    def refine_object(self, image: Image.Image, p: GenParams, strength: float) -> Image.Image:
        with self._lock:
            self._load()
            self._transparent(True)
            init = image.convert("RGBA").resize((p.width, p.height))
            latents = self._encoder.encode(init, self._img2img)
            img = self._img2img(prompt=p.prompt, negative_prompt=p.negative_prompt or None, image=latents,
                                strength=strength, num_inference_steps=effective_steps(p.steps, strength),
                                guidance_scale=p.guidance, generator=self._gen(p.seed), return_dict=False)[0][0]
            return img.convert("RGBA")

    def refine_background(self, image: Image.Image, p: GenParams, strength: float) -> Image.Image:
        with self._lock:
            self._load()
            self._transparent(False)
            try:
                init = image.convert("RGB").resize((p.width, p.height))
                img = self._img2img(prompt=p.prompt, negative_prompt=p.negative_prompt or None, image=init,
                                    strength=strength, num_inference_steps=effective_steps(p.steps, strength),
                                    guidance_scale=p.guidance, generator=self._gen(p.seed), return_dict=False)[0][0]
            finally:
                self._transparent(True)
            return opaque(img)

    def info(self) -> dict:
        return {"backend": self.name, "model": self.model, "device": getattr(self, "device", "not loaded"),
                "alpha_quality": self.alpha_quality, "load_seconds": round(self.load_seconds, 1)}
