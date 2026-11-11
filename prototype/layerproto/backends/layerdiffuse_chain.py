"""LayerDiffuse SDXL scene-to-layer chain (Zhang & Agrawala 2024, released SDXL conditional models).

    background(prompt)                      plain SDXL -> opaque base layer
    blend(scene, prompt)            bg2ble:   draws the new element INTO the current scene (lighting, perspective)
    extract(scene, blended, prompt) bgble2fg: returns only that new element as an RGBA layer

The two conditional models are weight deltas on the SDXL UNet (bg2ble: 206 tensors, bgble2fg: 1252 tensors,
~1.8B params) plus 4 / 8 extra input channels. Holding three UNets would not fit in 16 GB RAM, so deltas are
added and subtracted in place, streamed tensor by tensor from the safetensors file (memory overhead ~one tensor).
Weights: rootonchair/diffuser_layerdiffuse (converted from LayerDiffusion/layerdiffusion-v1, OpenRAIL-M).
"""
from __future__ import annotations

import os
import sys
import threading
import time
import types

import numpy as np
from PIL import Image

_VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "vendor",
                       "diffuser_layerdiffuse")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

REPO = "rootonchair/diffuser_layerdiffuse"
DELTAS = {"bg2ble": ("diffuser_layer_xl_bg2ble.safetensors", 4),
          "bgble2fg": ("diffuser_layer_xl_bgble2fg.safetensors", 8)}
LD_REPO = "LayerDiffusion/layerdiffusion-v1"


from .chain_base import ChainBackend, ChainParams


class LayerDiffuseChain(ChainBackend):
    name = "layerdiffuse-sdxl-chain"

    def __init__(self, model: str = "stabilityai/sdxl-turbo", device: str = "auto", alpha_quality: str = "fast",
                 variant: str | None = None):
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        self.model, self.alpha_quality, self._device_pref = model, alpha_quality, device
        # SDXL base is downloaded as its fp16 files only; they are upcast to float32 on CPU
        self.variant = variant if variant is not None else ("fp16" if "xl-base" in model else None)
        self.turbo = "turbo" in model.lower()
        self._lock = threading.Lock()
        self._pipe = None
        self._mode = "base"
        self.load_seconds = 0.0

    # ------------------------------------------------------------------ loading
    def _load(self):
        if self._pipe is not None:
            return
        import torch
        from diffusers import StableDiffusionXLPipeline
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        from layer_diffuse.models import TransparentVAEDecoder

        t0 = time.time()
        dev = self._device_pref
        if dev == "auto":
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        self.device, self.dtype = dev, (torch.float16 if dev == "cuda" else torch.float32)

        vkw = {"variant": self.variant} if self.variant else {}
        if self.dtype == torch.float16:
            # SDXL's own VAE overflows in fp16; the reference LayerDiffuse scripts use the fp16-fix VAE
            vae = TransparentVAEDecoder.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=self.dtype)
        else:
            vae = TransparentVAEDecoder.from_pretrained(self.model, subfolder="vae", torch_dtype=self.dtype, **vkw)
        if self.dtype == torch.float16:
            vae.config.force_upcast = False
        vae.set_transparent_decoder(load_file(hf_hub_download(LD_REPO, "vae_transparent_decoder.safetensors")))
        if self.alpha_quality == "fast":
            vae.estimate_augmented = lambda pixel, latent: vae.estimate_single_pass(pixel, latent).clip(0, 1)
        vae.mod_number = None  # opaque decode unless extracting a layer
        self._vae = vae

        pipe = StableDiffusionXLPipeline.from_pretrained(self.model, vae=vae, torch_dtype=self.dtype,
                                                         add_watermarker=False, **vkw).to(dev)
        if dev == "cpu":
            for comp in pipe.components.values():
                if hasattr(comp, "to") and hasattr(comp, "parameters"):
                    comp.to(dtype=self.dtype)
        self._pipe = pipe
        self._sched_default = pipe.scheduler
        # the reference bg2ble script blends with DPM++ 2M SDE Karras (SDXL base, 20 steps, CFG 7)
        from diffusers import DPMSolverMultistepScheduler
        self._sched_blend = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config, algorithm_type="sde-dpmsolver++", solver_order=2, use_karras_sigmas=True)
        unet = pipe.unet
        self._conv_base = unet.conv_in
        self._conv = {"base": unet.conv_in}
        for mode, (fname, extra) in DELTAS.items():
            self._conv[mode] = self._make_conv(fname, extra)
        self._patch_forward(unet)
        self.load_seconds = time.time() - t0

    def _make_conv(self, fname, extra):
        """conv_in for a conditional mode: base weights padded with zeros for the extra channels, plus delta."""
        import torch
        from huggingface_hub import hf_hub_download
        from safetensors import safe_open

        base = self._conv_base
        conv = torch.nn.Conv2d(base.in_channels + extra, base.out_channels, base.kernel_size, base.stride,
                               base.padding).to(device=self.device, dtype=self.dtype)
        with torch.no_grad(), safe_open(hf_hub_download(REPO, fname), "pt") as f:
            w = torch.zeros_like(conv.weight)
            w[:, :base.in_channels] = base.weight
            conv.weight.copy_(w + f.get_tensor("conv_in.weight").to(device=self.device, dtype=self.dtype))
            b = base.bias.clone()
            if "conv_in.bias" in f.keys():
                b = b + f.get_tensor("conv_in.bias").to(device=self.device, dtype=self.dtype)
            conv.bias.copy_(b)
        return conv

    def _patch_forward(self, unet):
        orig = unet.forward
        unet._ld_cond = None

        def forward(self_, sample, timestep, *args, **kwargs):
            if self_._ld_cond is not None:
                c = self_._ld_cond.to(device=sample.device, dtype=sample.dtype)
                if c.shape[0] != sample.shape[0]:  # classifier-free guidance doubles the batch
                    c = c.repeat(sample.shape[0] // c.shape[0], 1, 1, 1)
                sample = torch_cat([sample, c])
            return orig(sample, timestep, *args, **kwargs)

        import torch
        torch_cat = lambda xs: torch.cat(xs, dim=1)  # noqa: E731
        unet.forward = types.MethodType(forward, unet)

    def _stream_delta(self, mode: str, sign: float):
        import torch
        from huggingface_hub import hf_hub_download
        from safetensors import safe_open

        params = dict(self._pipe.unet.named_parameters())
        with torch.no_grad(), safe_open(hf_hub_download(REPO, DELTAS[mode][0]), "pt") as f:
            for key in f.keys():
                if key.startswith("conv_in."):
                    continue
                p = params[key]
                p.add_(f.get_tensor(key).to(device=p.device, dtype=p.dtype), alpha=sign)

    def _set_mode(self, mode: str):
        if mode == self._mode:
            return
        if self._mode != "base":
            self._stream_delta(self._mode, -1.0)
        if mode != "base":
            self._stream_delta(mode, +1.0)
        self._pipe.unet.conv_in = self._conv[mode]
        self._mode = mode

    # ------------------------------------------------------------------ helpers
    def _encode(self, img: Image.Image, w: int, h: int):
        import torch
        from layer_diffuse.utils import crop_and_resize_image, rgba2rgbfp32

        arr = crop_and_resize_image(rgba2rgbfp32(np.array(img.convert("RGBA"))), 1, h, w)
        t = torch.from_numpy(np.ascontiguousarray(arr[None].copy())).movedim(-1, 1)
        t = t.to(device=self.device, dtype=self.dtype) * 2.0 - 1.0
        with torch.no_grad():
            lat = self._pipe.vae.encode(t).latent_dist.mean
        return lat * self._pipe.vae.config.scaling_factor

    def _run(self, prompt, seed, w, h, steps, guidance, negative=""):
        import torch

        return self._pipe(prompt=prompt, negative_prompt=negative or None, width=w, height=h,
                          num_inference_steps=steps, guidance_scale=guidance,
                          generator=torch.Generator("cpu").manual_seed(int(seed)), return_dict=False)[0][0]

    # ------------------------------------------------------------------ the chain
    # ---- ChainBackend API (ChainParams) ----------------------------------------
    def background(self, p, seed=None, **kw) -> Image.Image:  # type: ignore[override]
        if isinstance(p, ChainParams):
            return self._background(p.prompt, p.seed, p.width, p.height, p.steps, p.guidance, p.negative_prompt)
        return self._background(p, seed, **kw)

    def blend(self, scene, p, seed=None, **kw) -> Image.Image:  # type: ignore[override]
        if isinstance(p, ChainParams):
            return self._blend(scene, p.prompt, p.seed, p.width, p.height, p.steps, p.guidance, p.negative_prompt)
        return self._blend(scene, p, seed, **kw)

    def extract(self, scene, blended, p, seed=None, **kw) -> Image.Image:  # type: ignore[override]
        if isinstance(p, ChainParams):
            return self._extract(scene, blended, p.prompt, p.seed, p.width, p.height, p.steps, p.guidance,
                                 p.negative_prompt)
        return self._extract(scene, blended, p, seed, **kw)

    # ---- implementation ------------------------------------------------------------
    def _background(self, prompt, seed, w=512, h=512, steps=4, guidance=1.0, negative="") -> Image.Image:
        with self._lock:
            self._load()
            self._set_mode("base")
            self._pipe.unet._ld_cond, self._vae.mod_number = None, None
            img = self._run(prompt, seed, w, h, steps, guidance, negative).convert("RGBA")
            img.putalpha(255)
            return img

    def _blend(self, scene: Image.Image, prompt, seed, w=512, h=512, steps=4, guidance=1.0, negative="") -> Image.Image:
        """bg2ble: the scene with the new element drawn into it (opaque RGB)."""
        with self._lock:
            self._load()
            self._set_mode("bg2ble")
            self._pipe.unet._ld_cond, self._vae.mod_number = self._encode(scene, w, h), None
            if not self.turbo:
                self._pipe.scheduler = self._sched_blend
            try:
                return self._run(prompt, seed, w, h, steps, guidance, negative).convert("RGBA")
            finally:
                self._pipe.unet._ld_cond = None
                self._pipe.scheduler = self._sched_default

    def _extract(self, scene: Image.Image, blended: Image.Image, prompt, seed, w=512, h=512, steps=4, guidance=1.0,
                 negative="") -> Image.Image:
        """bgble2fg: only the new element, as a transparent RGBA layer aligned with the scene."""
        import torch

        with self._lock:
            self._load()
            self._set_mode("bgble2fg")
            cond = torch.cat([self._encode(scene, w, h), self._encode(blended, w, h)], dim=1)
            self._pipe.unet._ld_cond, self._vae.mod_number = cond, 1
            try:
                return self._run(prompt, seed, w, h, steps, guidance, negative).convert("RGBA")
            finally:
                self._pipe.unet._ld_cond, self._vae.mod_number = None, None

    def relocate(self, scene: Image.Image, layer: Image.Image, box, prompt: str, seed: int, strength: float = 0.5,
                 pin_frac: float = 0.4, w=512, h=512, steps=20, guidance=7.0, negative="", extract: str = "model",
                 free_last: int | None = None, band: int = 9, paste_back: float = 0.0):
        """Training-free move/resize with re-harmonisation (our proposal, after DreamLayer's harmonisation step).

        scene: background RGB(A) without the layer; layer: the layer's RGBA (canvas-sized); box: new (x, y, bw, bh)
        in pixels for the layer's visible content. Steps:
          1. crop the layer to its alpha bbox, resize into `box`, paste over the scene (naive composite)
          2. bg2ble img2img from the naive composite at `strength`; during the first `pin_frac` of the denoising
             steps the object's (eroded) interior is pinned to the re-noised naive composite, so shape and identity
             stay while the rim and surroundings can re-light / grow contact shadows
          3. bgble2fg extracts the re-harmonised object (incl. shadow) as a new aligned RGBA layer
        Returns (naive_composite, harmonised_composite, new_layer).
        """
        import torch
        from PIL import ImageFilter
        from diffusers import StableDiffusionXLImg2ImgPipeline

        scene = scene.convert("RGBA").resize((w, h))
        layer = layer.convert("RGBA").resize((w, h))
        bbox = layer.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
        obj = layer.crop(bbox) if bbox else layer
        x, y, bw, bh = [int(v) for v in box]
        moved = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        moved.alpha_composite(obj.resize((max(1, bw), max(1, bh)), Image.LANCZOS), (x, y))
        naive = scene.copy()
        naive.alpha_composite(moved)
        # alpha > 40 (Qwen layers have soft alpha; >128 left ~1% of thin objects, so v1-v4 pinned almost nothing)
        interior = moved.getchannel("A").point(lambda a: 255 if a > 40 else 0).filter(ImageFilter.MinFilter(band))

        with self._lock:
            self._load()
            self._set_mode("bg2ble")
            self._pipe.unet._ld_cond, self._vae.mod_number = self._encode(scene, w, h), None
            i2i = StableDiffusionXLImg2ImgPipeline(**self._pipe.components)
            # deterministic default scheduler: pinning latents to a re-noised reference breaks the stochastic
            # DPM++ SDE blend scheduler (v1 trial: heavy artifacts at strength 0.6)
            i2i.scheduler = self._sched_default
            lat0 = self._encode(naive, w, h)
            m = torch.from_numpy(np.asarray(interior.resize((w // 8, h // 8)), dtype=np.float32) / 255.0)
            m = m[None, None].to(lat0.device, lat0.dtype)
            gen = torch.Generator("cpu").manual_seed(int(seed))
            noise = torch.randn(lat0.shape, generator=gen).to(lat0.device, lat0.dtype)
            n_real = max(1, int(steps * strength))
            # free_last=None: pin only the first pin_frac of the steps (v2). free_last=k: pin the interior on EVERY
            # step except the last k (after Collage Diffusion's per-layer noise level / DesignEdit's late fusion),
            # so only the edge band and the surroundings are re-generated (identity drift fix, v3)
            pin_until = int(n_real * pin_frac) if free_last is None else max(0, n_real - free_last)

            def pin(p, i, t, kw):
                if i < pin_until:
                    # img2img keeps the FULL timestep list but only runs its tail, so look up where we are by
                    # value (bug in v1-v3: ts[i + 1] pointed at a much noisier early timestep)
                    ts = p.scheduler.timesteps
                    k = int((ts == t).nonzero()[0][0]) if (ts == t).any() else i
                    ref = p.scheduler.add_noise(lat0, noise, ts[k + 1].reshape(1)) if k + 1 < len(ts) else lat0
                    kw["latents"] = kw["latents"] * (1 - m) + ref * m
                return kw

            try:
                harm = i2i(prompt=prompt, negative_prompt=negative or None, image=naive.convert("RGB"),
                           strength=strength, num_inference_steps=steps, guidance_scale=guidance,
                           generator=torch.Generator("cpu").manual_seed(int(seed)),
                           callback_on_step_end=pin, callback_on_step_end_tensor_inputs=["latents"],
                           return_dict=False)[0][0].convert("RGBA")
            finally:
                self._pipe.unet._ld_cond = None
                self._pipe.scheduler = self._sched_default
        if paste_back > 0:
            # blend the warped original object back over the re-harmonised image inside its alpha (identity kept;
            # the surroundings keep the new light / shadow). paste_back=1: exact original pixels inside the object
            a = (np.asarray(moved.getchannel("A"), dtype=np.float32)[..., None] / 255.0) * paste_back
            mix = np.asarray(harm.convert("RGB"), dtype=np.float32) * (1 - a) + np.asarray(moved.convert("RGB"), dtype=np.float32) * a
            harm = Image.fromarray(mix.clip(0, 255).astype(np.uint8)).convert("RGBA")
        if extract == "model":
            new_layer = self._extract(scene, harm, prompt, seed, w, h, steps, guidance, negative)
        else:
            new_layer = self.mask_extract(scene, harm, moved)
        return naive, harm, new_layer

    @staticmethod
    def mask_extract(scene: Image.Image, harm: Image.Image, moved: Image.Image, thr: float = 18.0,
                     ring: int = 41) -> Image.Image:
        """Cheap, deterministic layer from a re-harmonised composite: RGB from `harm`; alpha = the moved object's
        alpha, plus (within a ring around it) wherever `harm` differs from the background, which picks up the new
        contact shadow / glow. No model call."""
        from PIL import ImageFilter

        a_obj = np.asarray(moved.getchannel("A"), dtype=np.float32) / 255.0
        d = np.abs(np.asarray(harm.convert("RGB"), dtype=np.float32) -
                   np.asarray(scene.convert("RGB").resize(harm.size), dtype=np.float32)).mean(-1)
        a_diff = np.clip((d - thr) / thr, 0, 1)
        near = np.asarray(moved.getchannel("A").point(lambda v: 255 if v > 20 else 0)
                          .filter(ImageFilter.MaxFilter(ring)), dtype=np.float32) / 255.0
        a = np.maximum(a_obj, a_diff * near)
        out = harm.convert("RGBA")
        out.putalpha(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)))
        return out

    def info(self) -> dict:
        return {"backend": self.name, "model": self.model, "device": getattr(self, "device", "not loaded"),
                "mode": self._mode, "load_seconds": round(self.load_seconds, 1)}
