"""Profile `qwen21`: Qwen-Image-2.1-Turbo (7B, RGBA) on the two T4s of a Kaggle session; serves `qwen21-extract` on /decompose
and layer edits with the alpha retry.

    PIP = packages to install first        load() -> loaded pipeline (about 240 s: downloads + text encoder split over both GPUs)

Moved out of tools/make_qwen21_*_trial.py (the code that produced the measured runs, unchanged in behaviour):
  * transformer: unsloth GGUF Q4_K_S on GPU 0, its non-Linear GGUF parameters dequantised, `fp16_mixed` (Qwen models overflow plain fp16)
  * Qwen3-VL text encoder in fp16 split over both GPUs (device_map)
  * VAE: madebyollin/texture-fix-vae-for-qwen-image-2.1 (the stock VAE gives NaNs in fp16 on transparent pixels)
Qwen Research Licence (non-commercial) applies.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import time

PIP = ["transformers>=5.17", "gguf>=0.10", "accelerate", "git+https://github.com/huggingface/diffusers"]
REPO = "Qwen/Qwen-Image-2.1-Turbo"
GGUF_REPO = "unsloth/Qwen-Image-2.1-Turbo-GGUF"
GGUF_FILE = "qwen-image-2.1-turbo-Q4_K_S.gguf"
VAE_REPO = "madebyollin/texture-fix-vae-for-qwen-image-2.1"
WEIGHTS_KERNELS = ["weights-qwen21-text-encoder", "weights-qwen21-parts"]      # notebooks whose output holds the files (tools/make_weights_notebooks.py)
RGBA_PROMPT = "This is an RGBA image with transparency. {}. The image has alpha channel and the background is transparent."


def pip_install(packages=PIP):
    cmd = [sys.executable, "-m", "pip", "-q", "install"] + list(packages)
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def find_weights(log=print):
    """(base folder, gguf file, VAE folder). Attached Kaggle input (output of the weights-qwen21-* notebooks, no download) when it
    exists, else Hugging Face (about 17.5 GB, several minutes). The base folder is copied to local disk once: parallel tensor
    reads from the input mount stall."""
    g = glob.glob(f"/kaggle/input/**/{GGUF_FILE}", recursive=True)
    b = glob.glob("/kaggle/input/**/Qwen-Image-2.1-Turbo/model_index.json", recursive=True)
    v = glob.glob("/kaggle/input/**/texture-fix-vae/config.json", recursive=True)
    if g and b and v:
        local = "/tmp/Qwen-Image-2.1-Turbo"
        shutil.copytree(os.path.dirname(b[0]), local, dirs_exist_ok=True)
        log("weights from the attached Kaggle input (no download)")
        return local, g[0], os.path.dirname(v[0])
    log("weights input not attached: downloading from Hugging Face (attach the weights-qwen21-* notebooks as kernel sources to skip this)")
    from huggingface_hub import hf_hub_download, snapshot_download
    base = snapshot_download(REPO, ignore_patterns=["transformer/*.safetensors", "vae/*.safetensors", "assets/*"])
    return base, hf_hub_download(GGUF_REPO, GGUF_FILE), VAE_REPO


def load(log=print, te_gpu0: str = "5GiB"):
    """Return the QwenImage21Pipeline with everything placed (transformer + VAE on cuda:0, text encoder split over both GPUs).
    te_gpu0: share of the 16.3 GiB text encoder allowed on GPU 0; the rest goes to GPU 1 (studio profile: "2.5GiB", frees GPU 0 for SDXL-Turbo)."""
    import torch

    from ..fp16_mixed import apply_fp16_mixed

    t0 = time.time()
    base, gguf, vae_src = find_weights(log)
    log(f"weights ready {time.time() - t0:.0f} s")
    from diffusers import (AutoencoderKLQwenImage21, GGUFQuantizationConfig, QwenImage21Pipeline,
                           QwenImage21Transformer2DModel)
    from diffusers.quantizers.gguf.utils import GGUFLinear, GGUFParameter, dequantize_gguf_tensor
    from transformers import AutoModelForImageTextToText

    d0, dt = torch.device("cuda:0"), torch.float16
    t = QwenImage21Transformer2DModel.from_single_file(gguf, config=base, subfolder="transformer",
                                                       quantization_config=GGUFQuantizationConfig(compute_dtype=dt), torch_dtype=dt)
    fixed = 0                                         # diffusers' GGUF loader only dequantises nn.Linear
    for m in t.modules():
        for n, p in list(m.named_parameters(recurse=False)):
            if isinstance(m, GGUFLinear) and n == "weight":
                continue
            if isinstance(p, GGUFParameter):
                setattr(m, n, torch.nn.Parameter(dequantize_gguf_tensor(p).to(dt), requires_grad=False))
                fixed += 1
    log(f"dequantised non-linear GGUF params: {fixed}")
    apply_fp16_mixed(t)
    t.to(d0).eval()
    te = AutoModelForImageTextToText.from_pretrained(f"{base}/text_encoder", torch_dtype=dt, device_map="auto",
                                                     max_memory={0: te_gpu0, 1: "14GiB", "cpu": "24GiB"})
    vae = AutoencoderKLQwenImage21.from_pretrained(vae_src, torch_dtype=dt)
    pipe = QwenImage21Pipeline.from_pretrained(base, transformer=t, text_encoder=te, vae=vae, torch_dtype=dt)
    pipe.vae.to(d0)
    type(pipe)._execution_device = property(lambda self: d0)
    log(f"loaded {time.time() - t0:.0f} s; GiB {[round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)]}")
    return pipe


def edit_layer(pipe, layer, prompt: str, seed: int = 42, size: int = 512):
    """One RGBA layer edit (relight / reprompt) for layer_edit.edit_layer_keep_alpha: editor(layer, seed) -> layer."""
    import torch

    with torch.inference_mode():
        return pipe(prompt=RGBA_PROMPT.format(prompt), image=[layer], width=size, height=size, output_resolution=size,
                    use_kv_cache=True, generator=torch.Generator(pipe._execution_device).manual_seed(seed)).images[0]


def make(log=print, te_gpu0: str = "5GiB"):
    """Factory used by the profile registry: a MethodRouter serving `qwen21-extract` on the loaded pipeline.
    The router carries `.editor` (RGBA layer edit with the alpha check-and-retry) for the /edit route."""
    from ..backends.decomposer import MethodRouter
    from ..backends.qwen21_decomposer import Qwen21Decomposer
    pipe = load(log, te_gpu0)
    router = MethodRouter({"qwen21-extract": Qwen21Decomposer(pipe)})

    def editor(layer, prompt, seed):
        from ..layer_edit import edit_layer_keep_alpha, transparent_share
        if transparent_share(layer) < 0.02:               # an opaque layer (the background): a plain edit; the RGBA prompt would make it transparent
            import torch
            with torch.inference_mode():
                out = pipe(prompt=prompt, image=[layer.convert("RGB")], width=512, height=512, output_resolution=512, use_kv_cache=True,
                           generator=torch.Generator(pipe._execution_device).manual_seed(seed)).images[0]
            return out.convert("RGBA"), {"accepted": True, "opaque": True}
        seeds = (seed,) + tuple(x for x in (42, 7, 123, 2024) if x != seed)
        return edit_layer_keep_alpha(lambda im, sd: edit_layer(pipe, im, prompt, sd), layer, seeds=seeds)

    router.editor = editor
    return router
