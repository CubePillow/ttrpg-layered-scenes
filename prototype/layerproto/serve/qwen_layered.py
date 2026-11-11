"""Profile `qwen-layered`: Qwen-Image-Layered (GGUF Q4_K_S, fp16_mixed, split over both T4s) serving three `/decompose` methods:

    qwen-layered   base model              (Euler, or Heun with DecomposeParams.sampler="heun")
    stable-layers  base + Stable-Layers LoRA (clean semantic split, colour shift; Heun recommended)
    qwen-lightning base + Lightning LoRA 1.0 (2-4 steps, thin subjects)

All three share one loaded transformer; switching method swaps the LoRA (a few seconds). Moved out of the batch notebooks
(tools/make_qwen_layered_test.py / make_qwen_layered_batch.py), where these settings produced the measured runs.

Weights: the transformer GGUF and the base repo (text encoder, VAE, tokenizer) are public Kaggle notebook outputs
(`markandreduesing/qwen-layered-weights-transformer`, `-base`, attached as kernel sources, so a new session needs no Hugging Face
download); without them the Hugging Face repos are used. The text encoder (16.6 GB) is only used at load time to encode the known
captions, then unloaded: a request with a caption that was not encoded at load falls back to the generic caption (a live
text-encoder pass is future work).
"""
from __future__ import annotations

import glob
import math
import os
import shutil
import time

from PIL import Image

from .. import qwen_layered as Q
from ..backends.decomposer import DecomposeParams

PIP = ["diffusers==0.37.0", "transformers>=4.51", "accelerate", "gguf"]
KERNEL_SOURCES = ["markandreduesing/qwen-layered-weights-transformer", "markandreduesing/qwen-layered-weights-base"]
METHODS = ("qwen-layered", "stable-layers", "qwen-lightning")
GENERIC_CAPTION = "An illustration."
LIGHT_SCHED = dict(base_image_seq_len=256, base_shift=math.log(3), invert_sigmas=False, max_image_seq_len=8192,
                   max_shift=math.log(3), num_train_timesteps=1000, shift=1.0, shift_terminal=None,
                   stochastic_sampling=False, time_shift_type="exponential", use_beta_sigmas=False,
                   use_dynamic_shifting=True, use_exponential_sigmas=False, use_karras_sigmas=False)


def _move(x, d):
    import torch
    if torch.is_tensor(x):
        return x.to(d, non_blocking=True)
    if isinstance(x, dict):
        return {k: _move(v, d) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return type(x)(_move(v, d) for v in x)
    return x


def _to_own_device(m, args, kwargs):
    d = next(m.parameters()).device
    return _move(args, d), _move(kwargs, d)


def split_across_gpus(model, devices=("cuda:0", "cuda:1")):
    """Blocks 0-29 on GPU 0, 30-59 on GPU 1, activations hop between the cards through forward pre-hooks."""
    blocks = model.transformer_blocks
    half = len(blocks) // 2
    for name, child in model.named_children():
        if name != "transformer_blocks":
            child.to(devices[0])
    for i, b in enumerate(blocks):
        b.to(devices[0] if i < half else devices[1])
    if not getattr(model, "_split_hooks", False):
        for m in list(blocks) + [model.norm_out, model.proj_out]:
            m.register_forward_pre_hook(_to_own_device, with_kwargs=True)
        model._split_hooks = True
    return model


class QwenLayeredDecomposer:
    def __init__(self, captions: list[str] | None = None, log=print):
        import torch
        from huggingface_hub import hf_hub_download

        from ..fp16_mixed import apply_fp16_mixed

        t0 = time.time()
        self.log, self.torch = log, torch
        dt = torch.float16
        g = glob.glob("/kaggle/input/**/qwen-image-layered-Q4_K_S.gguf", recursive=True)
        b = glob.glob("/kaggle/input/**/Qwen-Image-Layered/model_index.json", recursive=True)
        gguf = g[0] if g else None
        src = os.path.dirname(b[0]) if b else Q.REPO
        log(f"transformer from: {gguf or 'Hugging Face'} | base from: {src}")
        if src.startswith("/kaggle/input"):             # parallel tensor reads from the input mount stall; copy once
            local = "/tmp/Qwen-Image-Layered"
            shutil.copytree(src, local, dirs_exist_ok=True)
            src = local
            log(f"base copied to local disk after {time.time() - t0:.0f} s")
        from diffusers import AutoencoderKLQwenImage, GGUFQuantizationConfig, QwenImageTransformer2DModel
        from transformers import Qwen2_5_VLForConditionalGeneration

        te = Qwen2_5_VLForConditionalGeneration.from_pretrained(src, subfolder="text_encoder", torch_dtype=dt, device_map="auto",
                                                                max_memory={0: "13GiB", 1: "14GiB"})
        vae = AutoencoderKLQwenImage.from_pretrained(src, subfolder="vae", torch_dtype=dt).to("cuda:0")
        self.pipe = Q.make_pipeline(te, vae, src)
        self.emb = {}
        for c in dict.fromkeys([GENERIC_CAPTION] + list(captions or [])):
            self.emb[c] = tuple(x.to("cuda:0") for x in Q.encode(self.pipe, c, device="cuda:0"))
        del te
        Q.unload_text_encoder(self.pipe, dt)
        log(f"text encoder used and unloaded after {time.time() - t0:.0f} s; {len(self.emb)} caption(s) encoded")
        tr = QwenImageTransformer2DModel.from_single_file(
            gguf or hf_hub_download("unsloth/Qwen-Image-Layered-GGUF", "qwen-image-layered-Q4_K_S.gguf"),
            quantization_config=GGUFQuantizationConfig(compute_dtype=dt), torch_dtype=dt, config=src, subfolder="transformer").to("cuda:0")
        Q.fix_gguf_non_linear(tr, dt)
        apply_fp16_mixed(tr)
        split_across_gpus(tr)
        self.tr = tr
        self.orig_sched = self.pipe.scheduler
        import json
        cfg = json.load(open(hf_hub_download("StabilityLabs/Stable-Layers", "model/adapter_config.json")))
        self.stable_path = hf_hub_download("StabilityLabs/Stable-Layers", "model/adapter_model.safetensors")
        self.stable_scale = cfg.get("lora_alpha", cfg.get("r", 1)) / cfg.get("r", 1)
        self.light_path = hf_hub_download("lightx2v/Qwen-Image-Lightning", "Qwen-Image-Lightning-4steps-V2.0-bf16.safetensors")
        self.active = "qwen-layered"
        log(f"loaded in {time.time() - t0:.0f} s; GiB {[round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)]}")

    def _activate(self, method: str):
        from diffusers import FlowMatchEulerDiscreteScheduler

        from ..fp16_mixed import add_lora, remove_lora
        if method == self.active:
            return
        remove_lora(self.tr)
        self.pipe.scheduler = self.orig_sched
        if method == "stable-layers":
            add_lora(self.tr, self.stable_path, scale=self.stable_scale)
        elif method == "qwen-lightning":
            add_lora(self.tr, self.light_path, scale=1.0)
            self.pipe.scheduler = FlowMatchEulerDiscreteScheduler.from_config(LIGHT_SCHED)
        self.active = method

    def __call__(self, image: Image.Image, p: DecomposeParams) -> list[Image.Image]:
        if p.method not in METHODS:
            raise ValueError(f"unknown method {p.method!r}; this profile offers {list(METHODS)}")
        self._activate(p.method)
        emb = self.emb.get(p.caption) or self.emb[GENERIC_CAPTION]
        sampler = getattr(p, "sampler", "euler")
        layers, st = Q.decompose(self.pipe, self.tr, image.convert("RGB").resize((p.resolution, p.resolution)), p.caption or GENERIC_CAPTION,
                                 emb, steps=p.steps, layers=p.n_layers, resolution=p.resolution, seed=p.seed or 777, true_cfg=float(getattr(p, "cfg", 1.0)),
                                 offload=False, sampler=sampler)
        self.last_stats = st
        split_across_gpus(self.tr)                      # decompose() unregisters the transformer; keep the split in place
        size = image.size
        return [L.convert("RGBA").resize(size) for L in layers]


def make_diag(log=print):
    """Diagnosis profile: also encodes the forest caption and the empty caption."""
    from .profiles import CAPTION, PROFILES
    caps = [CAPTION, ""] + [c.params.caption for c in PROFILES["qwen-layered-diag"].cases]
    return QwenLayeredDecomposer(captions=caps, log=log)


def make_for(profile: str):
    """Factory for a profile whose cases bring their own captions (all of them are encoded at load time)."""
    def _make(log=print):
        from .profiles import CAPTION, PROFILES
        caps = [CAPTION, ""] + [c.params.caption for c in PROFILES[profile].cases]
        return QwenLayeredDecomposer(captions=caps, log=log)
    return _make


make_640 = make_for("qwen-layered-640")


def make(log=print):
    """Factory used by the profile registry: encodes the shared fox & cottage caption at load time."""
    from .profiles import CAPTION
    return QwenLayeredDecomposer(captions=[CAPTION], log=log)
