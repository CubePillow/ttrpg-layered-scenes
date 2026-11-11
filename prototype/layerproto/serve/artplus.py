"""Profile `artplus`: ART+ (PrismLayers) text + boxes -> RGBA layers on two T4s; method `artplus` on /decompose.

ART+ does not split the given image: it generates a new layered scene from the caption and the boxes (the input image only sets the
output size). Moved out of tools/make_artplus_trial.py (run 11, 512 px, 16 steps, 343 s; 1024 px, 8 steps, 1251 s):
  * FLUX.1-dev GGUF Q4_K_S re-classed into PrismLayers' custom transformer on GPU 0, fp16_mixed, three unmerged LoRAs
    (pre_fuse, ART base from CLD, ART+) and ART+'s own layer_pe
  * text encoders on GPU 1 (prompt embeddings hop to GPU 0), fp32 VAEs, transformer offloaded to the CPU before the decode
  * ART+'s own transparent decoder (CLD's decoder gave fully opaque layers)
Weights come from the authors' Google Drive folders (gdown) with the Hugging Face mirror `24yearsold/PrismLayers_ckpt` as fallback.
FLUX.1-dev Non-Commercial licence applies.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

from ..backends.decomposer import DecomposeParams

PIP = ["transformers==4.57.1 diffusers==0.32.2 peft==0.14.0 gguf>=0.10 sentencepiece protobuf mmengine gdown einops"]
ENV = {"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
REPO = "/kaggle/working/PrismLayers"


def _sh(cmd):
    print("$", cmd, flush=True)
    return subprocess.run(cmd, shell=True).returncode


def setup():
    if not os.path.exists(REPO):
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/redredsheep/PrismLayers", REPO], check=True)
    if f"{REPO}/multi_layer_gen" not in sys.path:
        sys.path.insert(0, f"{REPO}/multi_layer_gen")


def _boxes16(boxes, scale):
    R = int(round(512 * scale))
    return [(int(x0 * scale) // 16 * 16, int(y0 * scale) // 16 * 16, min(R, (int(x1 * scale) // 16 + 1) * 16),
             min(R, (int(y1 * scale) // 16 + 1) * 16)) for x0, y0, x1, y1 in boxes]


class ArtPlusDecomposer:
    def __init__(self, log=print):
        import torch
        import torch.nn as nn
        from diffusers import FlowMatchEulerDiscreteScheduler, FluxTransformer2DModel, GGUFQuantizationConfig
        from huggingface_hub import hf_hub_download, snapshot_download
        from safetensors.torch import load_file

        from ..fp16_mixed import add_lora, apply_fp16_mixed
        setup()
        from custom_model_mmdit import CustomFluxTransformer2DModel
        from custom_model_transp_vae import AutoencoderKLTransformerTraining as CustomVAE
        from custom_pipeline import CustomFluxPipelineCfgLayer

        t0 = time.time()
        self.torch, self.log = torch, log
        self.D0, self.D1, dt = torch.device("cuda:0"), torch.device("cuda:1"), torch.float16
        D0, D1 = self.D0, self.D1
        gguf = hf_hub_download("city96/FLUX.1-dev-gguf", "flux1-dev-Q4_K_S.gguf")
        base = snapshot_download("ostris/Flex.1-alpha", allow_patterns=["model_index.json", "text_encoder/*", "text_encoder_2/*", "tokenizer/*",
                                                                        "tokenizer_2/*", "vae/*", "scheduler/*"])
        cld = snapshot_download("thuteam/CLD", allow_patterns=["pre_trained_LoRA/*", "trans_vae/*"])
        W = "/kaggle/working/art_ckpt"
        os.makedirs(W, exist_ok=True)
        ok = (_sh(f"gdown --folder -q https://drive.google.com/drive/folders/1dHqBLJJtdCr0PMuZ5S3iq--7kSHbOISU -O {W}/pre_fuse_lora") == 0 and
              _sh(f"gdown --folder -q https://drive.google.com/drive/folders/1d-lIRYVyhKqpdZO50h4p4qZz9mXU3w4H -O {W}/artplus") == 0)

        def find(pat):
            f = sorted(glob.glob(f"{W}/**/{pat}", recursive=True))
            return f[0] if f else None
        if not (ok and find("pre_fuse_lora/*.safetensors") and find("artplus/*layer_pe*")):
            W = snapshot_download("24yearsold/PrismLayers_ckpt", allow_patterns=["pre_fuse_lora/*", "artplus_PrismLayersPro100k_ckpt/*", "base/*"])
        pre_fuse, art_lora, art_pe = find("pre_fuse_lora/*.safetensors"), find("artplus*/pytorch_lora_weights.safetensors"), find("artplus*/layer_pe*")
        load_any = lambda p: load_file(p) if p.endswith(".safetensors") else torch.load(p, map_location="cpu")
        cfg = "/kaggle/working/flux_dev_cfg"
        os.makedirs(f"{cfg}/transformer", exist_ok=True)
        json.dump({"_class_name": "FluxTransformer2DModel", "attention_head_dim": 128, "axes_dims_rope": [16, 56, 56], "guidance_embeds": True,
                   "in_channels": 64, "joint_attention_dim": 4096, "num_attention_heads": 24, "num_layers": 19, "num_single_layers": 38,
                   "patch_size": 1, "pooled_projection_dim": 768}, open(f"{cfg}/transformer/config.json", "w"))
        sched = FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000, shift=3.0, use_dynamic_shifting=True, base_shift=0.5,
                                                max_shift=1.15, base_image_seq_len=256, max_image_seq_len=4096)
        t = FluxTransformer2DModel.from_single_file(gguf, config=cfg, subfolder="transformer",
                                                    quantization_config=GGUFQuantizationConfig(compute_dtype=dt), torch_dtype=dt)
        t.__class__ = CustomFluxTransformer2DModel
        t.register_to_config(max_layer_num=52)
        t.max_layer_num = 52
        pe = load_any(art_pe)
        pe = pe.get("layer_pe", next(iter(pe.values()))) if isinstance(pe, dict) else pe
        t.layer_pe = nn.Parameter(pe.to(torch.float32).view(1, 52, 1, 1, -1), requires_grad=False)
        apply_fp16_mixed(t)
        for name, path in (("pre_fuse", pre_fuse), ("art_base(CLD)", f"{cld}/pre_trained_LoRA/pytorch_lora_weights.safetensors"), ("artplus", art_lora)):
            hit, miss = add_lora(t, path, 1.0)
            log(f"LoRA {name}: matched {hit}, missing {len(miss)}")
        t.to(D0).eval()
        pipe = CustomFluxPipelineCfgLayer.from_pretrained(base, transformer=t, scheduler=sched, torch_dtype=dt)
        pipe.vae.to(D0, torch.float32)
        pipe.text_encoder.to(D1)
        pipe.text_encoder_2.to(D1)
        CustomFluxPipelineCfgLayer._execution_device = property(lambda self: D0)
        pipe.vae_scale_factor = 16
        orig_enc = pipe.encode_prompt

        def enc(*a, device=None, **kw):
            out = orig_enc(*a, device=D1, **kw)
            return tuple(o.to(D0) if torch.is_tensor(o) else o for o in out)
        pipe.encode_prompt = enc
        tvae = CustomVAE(argparse.Namespace(max_layers=48, decoder_arch="vit", pos_embedding="rope", layer_embedding="rope", single_layer_decoder=None))
        tv_path = None
        if _sh("gdown --folder -q https://drive.google.com/drive/folders/1K-d1RurP6W8LaVNc3y70Y60K3RqF2eo- -O /kaggle/working/art_tvae") == 0:
            c = sorted(glob.glob("/kaggle/working/art_tvae/**/*.pt*", recursive=True)) + sorted(glob.glob("/kaggle/working/art_tvae/**/*.safetensors", recursive=True))
            tv_path = c[0] if c else None
        if tv_path is None:
            try:
                tv_path = hf_hub_download("24yearsold/PrismLayers_ckpt", "trans_vae/0008000.safetensors")
            except Exception as e:  # noqa: BLE001
                log(f"mirror decoder failed: {e}")
        if tv_path is None:
            tv_path = glob.glob(f"{cld}/trans_vae/*.pt")[0]
        tv = load_file(tv_path) if tv_path.endswith(".safetensors") else torch.load(tv_path, map_location="cpu", weights_only=False)
        tvae.load_state_dict(tv.get("model", tv) if isinstance(tv, dict) and "model" in tv else tv, strict=False)
        tvae.to(D0, torch.float32).eval()

        def to32(m, args, kwargs):
            c = lambda x: x.float() if torch.is_tensor(x) and x.is_floating_point() else x
            return tuple(c(a) for a in args), {k: c(v) for k, v in kwargs.items()}
        for v in (tvae, pipe.vae):
            v.register_forward_pre_hook(to32, with_kwargs=True)
            for name in ("encode", "decode"):
                if hasattr(v, name):
                    f = getattr(v, name)
                    setattr(v, name, (lambda f: lambda *a, **k: f(*[x.float() if torch.is_tensor(x) and x.is_floating_point() else x for x in a], **k))(f))
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()
        for v in (tvae, pipe.vae):
            dec = v.decode

            def off(*a, _d=dec, **k):
                if next(t.parameters()).device.type == "cuda":
                    t.to("cpu")
                    torch.cuda.empty_cache()
                return _d(*a, **k)
            v.decode = off
        self.t, self.pipe, self.tvae = t, pipe, tvae
        log(f"loaded {time.time() - t0:.0f} s; GiB {[round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)]}")

    def __call__(self, image: Image.Image, p: DecomposeParams) -> list[Image.Image]:
        if p.method != "artplus":
            raise ValueError(f"unknown method {p.method!r}; this profile offers ['artplus']")
        if not p.boxes:
            raise ValueError("artplus needs boxes (one [x0, y0, x1, y1] per layer, back to front, in 512-px coordinates)")
        torch = self.torch
        R = int(p.resolution)
        scale = R / 512.0
        full = [0, 0, 512, 512]
        layout = _boxes16([full, full] + [list(b) for b in p.boxes], scale)
        caption = "This is a painting style image. " + p.caption + " Blue sky with white clouds and a green lawn fill the whole background."
        self.t.to(self.D0)
        torch.cuda.empty_cache()
        with torch.inference_mode():
            x_hat, images, _ = self.pipe(prompt=caption, validation_box=layout, generator=torch.Generator(self.D0).manual_seed(p.seed or 42),
                                         height=R, width=R, num_inference_steps=p.steps, guidance_scale=4.0, num_layers=len(layout), sdxl_vae=self.tvae)
        x_hat = ((x_hat + 1) / 2).squeeze(0).permute(1, 0, 2, 3).float()
        size = image.size
        layers = [images[1].convert("RGBA").resize(size)]
        for i in range(2, x_hat.shape[0]):
            arr = (x_hat[i].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
            layers.append(Image.fromarray(arr, "RGBA").resize(size))
        return layers


def make(log=print):
    from ..backends.decomposer import MethodRouter
    return MethodRouter({"artplus": ArtPlusDecomposer(log)})
