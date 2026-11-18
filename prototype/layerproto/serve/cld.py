"""Profile `cld`: Controllable Layer Decomposition (image + caption + boxes -> RGBA layers) on two T4s; method `cld` on /decompose.

Moved out of tools/make_cld_trial.py and its 768/1024 px probes (`make_cld_768c_probe.py` = the layout that fits, 10.8 GiB peak at 768 px):
  * FLUX.1-dev GGUF Q4_K_S (city96) re-classed into CLD's custom transformer on GPU 0, fp16_mixed, three unmerged LoRAs
  * CLD's MultiLayerAdapter (ControlNet-Inpainting-Alpha + its LoRA) on GPU 1 with its own layer_pe copy, inputs/outputs hop between the cards
  * text encoders (T5 + CLIP) on the CPU in bf16 so GPU 1 has room; prompt embeddings are cast to fp16 on GPU 0
  * fp32 VAEs with the transformer and adapter offloaded to the CPU before decoding (they are moved back for the next request)
Run with PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True (profiles.py sets it). FLUX.1-dev Non-Commercial licence applies.
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
REPO = "/kaggle/working/CLD"


def setup(log=print):
    """Clone CLD and patch its adapter import for diffusers 0.32 (BaseOutput moved); put it on sys.path."""
    if not os.path.exists(REPO):
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/monkek123King/CLD", REPO], check=True)
    f = f"{REPO}/models/multiLayer_adapter.py"
    s = open(f).read().replace("from diffusers.models.controlnet import BaseOutput, zero_module",
                               "from diffusers.utils import BaseOutput; from diffusers.models.controlnets.controlnet import zero_module")
    open(f, "w").write(s)
    if REPO not in sys.path:
        sys.path.insert(0, REPO)


def _mv(x, d):
    import torch
    if torch.is_tensor(x):
        return x.to(d)
    if isinstance(x, (list, tuple)):
        return type(x)(_mv(i, d) for i in x)
    if isinstance(x, dict):
        y = {k: _mv(v, d) for k, v in x.items()}
        try:
            return type(x)(**y)
        except TypeError:
            return y
    return x


def _boxes16(boxes, scale):
    """Boxes in input pixels -> multiples of 16 at the generation size (the latent grid of the layout-aware FLUX is 16 px)."""
    R = int(round(512 * scale))
    return [(int(x0 * scale) // 16 * 16, int(y0 * scale) // 16 * 16, min(R, (int(x1 * scale) // 16 + 1) * 16),
             min(R, (int(y1 * scale) // 16 + 1) * 16)) for x0, y0, x1, y1 in boxes]


class CldDecomposer:
    def __init__(self, log=print):
        import torch
        import torch.nn as nn
        from diffusers import FlowMatchEulerDiscreteScheduler, FluxTransformer2DModel, GGUFQuantizationConfig
        from huggingface_hub import hf_hub_download, snapshot_download
        from safetensors.torch import load_file

        from ..fp16_mixed import add_lora, apply_fp16_mixed
        setup(log)
        from models.mmdit import CustomFluxTransformer2DModel
        from models.multiLayer_adapter import MultiLayerAdapter
        from models.pipeline import CustomFluxPipelineCfgLayer
        from models.transp_vae import AutoencoderKLTransformerTraining as CustomVAE

        t0 = time.time()
        self.torch, self.log = torch, log
        self.D0, self.D1, dt = torch.device("cuda:0"), torch.device("cuda:1"), torch.float16
        D0, D1 = self.D0, self.D1
        gguf = hf_hub_download("city96/FLUX.1-dev-gguf", "flux1-dev-Q4_K_S.gguf")
        base = snapshot_download("ostris/Flex.1-alpha", allow_patterns=["model_index.json", "text_encoder/*", "text_encoder_2/*", "tokenizer/*",
                                                                        "tokenizer_2/*", "vae/*", "scheduler/*"])
        cld = snapshot_download("thuteam/CLD")
        adp = snapshot_download("alimama-creative/FLUX.1-dev-Controlnet-Inpainting-Alpha")
        load_any = lambda p: load_file(p) if p.endswith(".safetensors") else torch.load(p, map_location="cpu")
        cfg = "/kaggle/working/flux_dev_cfg"
        os.makedirs(f"{cfg}/transformer", exist_ok=True)
        json.dump({"_class_name": "FluxTransformer2DModel", "attention_head_dim": 128, "axes_dims_rope": [16, 56, 56], "guidance_embeds": True,
                   "in_channels": 64, "joint_attention_dim": 4096, "num_attention_heads": 24, "num_layers": 19, "num_single_layers": 38,
                   "patch_size": 1, "pooled_projection_dim": 768}, open(f"{cfg}/transformer/config.json", "w"))
        sched = FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000, shift=3.0, use_dynamic_shifting=True, base_shift=0.5,
                                                max_shift=1.15, base_image_seq_len=256, max_image_seq_len=4096)
        log(f"downloads done {time.time() - t0:.0f} s")
        t = FluxTransformer2DModel.from_single_file(gguf, config=cfg, subfolder="transformer",
                                                    quantization_config=GGUFQuantizationConfig(compute_dtype=dt), torch_dtype=dt)
        t.__class__ = CustomFluxTransformer2DModel
        t.register_to_config(max_layer_num=52)
        t.max_layer_num = 52
        pe = load_any(f"{cld}/decouple_LoRA/layer_pe.pth")
        pe = pe.get("layer_pe", next(iter(pe.values()))) if isinstance(pe, dict) else pe
        t.layer_pe = nn.Parameter(pe.to(torch.float32).view(1, 52, 1, 1, -1), requires_grad=False)
        apply_fp16_mixed(t)
        for name, path in (("pre_trained", f"{cld}/pre_trained_LoRA/pytorch_lora_weights.safetensors"),
                           ("prism_ft", f"{cld}/prism_ft_LoRA/pytorch_lora_weights.safetensors"),
                           ("decouple", f"{cld}/decouple_LoRA/transformer/pytorch_lora_weights.safetensors")):
            hit, miss = add_lora(t, path, 1.0)
            log(f"LoRA {name}: matched {hit}, missing {len(miss)}")
        t.to(D0).eval()
        adapter = MultiLayerAdapter.from_pretrained(adp, torch_dtype=dt)
        apply_fp16_mixed(adapter)
        add_lora(adapter, f"{cld}/decouple_LoRA/adapter/pytorch_lora_weights.safetensors", 1.0)
        adapter.set_layerPE(nn.Parameter(t.layer_pe.detach().clone(), requires_grad=False), t.max_layer_num)   # own copy: .to(D1) must not move t.layer_pe
        adapter.to(D1).eval()
        adapter.register_forward_pre_hook(lambda m, a, k: (_mv(a, D1), _mv(k, D1)), with_kwargs=True)
        adapter.register_forward_hook(lambda m, a, k, out: _mv(out, D0), with_kwargs=True)
        pipe = CustomFluxPipelineCfgLayer.from_pretrained(base, transformer=t, scheduler=sched, torch_dtype=dt)
        pipe.set_multiLayerAdapter(adapter)
        pipe.vae.to(D0, torch.float32)
        pipe.text_encoder.to("cpu", torch.bfloat16)
        pipe.text_encoder_2.to("cpu", torch.bfloat16)
        CustomFluxPipelineCfgLayer._execution_device = property(lambda self: D0)
        pipe.vae_scale_factor = 16                    # PrismLayers was written for diffusers 0.31
        orig_enc = pipe.encode_prompt

        enc_cache = {}                                  # the CPU text-encoder pass is the slow part; a repeated prompt costs nothing

        def enc(*a, device=None, **kw):
            key = repr((a, sorted((k, repr(v)) for k, v in kw.items())))
            if key not in enc_cache:
                out = orig_enc(*a, device=torch.device("cpu"), **kw)
                enc_cache[key] = tuple(o.to(D0, torch.float16) if torch.is_tensor(o) else o for o in out)
            return enc_cache[key]
        pipe.encode_prompt = enc
        self.enc_cache = enc_cache
        vae_args = argparse.Namespace(max_layers=48, decoder_arch="vit", pos_embedding="rope", layer_embedding="rope", single_layer_decoder=None)
        tvae = CustomVAE(vae_args)
        path = glob.glob(f"{cld}/trans_vae/*.pt")[0]
        tv = load_file(path) if path.endswith(".safetensors") else torch.load(path, map_location="cpu", weights_only=False)
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
        for v in (tvae, pipe.vae):                    # offload the transformer and adapter before decoding (fp32 decode needs the room)
            dec = v.decode

            def off(*a, _d=dec, **k):
                if next(t.parameters()).device.type == "cuda":
                    t.to("cpu")
                    adapter.to("cpu")
                    torch.cuda.empty_cache()
                return _d(*a, **k)
            v.decode = off
        self.t, self.adapter, self.pipe, self.tvae = t, adapter, pipe, tvae
        log(f"loaded {time.time() - t0:.0f} s; GiB {[round(torch.cuda.memory_allocated(i) / 2**30, 1) for i in range(2)]}")

    def __call__(self, image: Image.Image, p: DecomposeParams) -> list[Image.Image]:
        if p.method != "cld":
            raise ValueError(f"unknown method {p.method!r}; this profile offers ['cld']")
        if not p.boxes:
            raise ValueError("cld needs boxes (one [x0, y0, x1, y1] per layer, back to front, in input pixels)")
        torch = self.torch
        R = int(p.resolution)
        scale = R / 512.0
        full = [0, 0, 512, 512]
        layout = _boxes16([full, full] + [list(b) for b in p.boxes], scale)
        self.t.to(self.D0)
        self.adapter.to(self.D1)
        torch.cuda.empty_cache()
        with torch.inference_mode():
            x_hat, images, _ = self.pipe(prompt=p.caption, adapter_image=image.convert("RGB").resize((R, R)), adapter_conditioning_scale=0.9,
                                         validation_box=layout, generator=torch.Generator(self.D0).manual_seed(p.seed or 42), height=R, width=R,
                                         num_inference_steps=p.steps, guidance_scale=4.0, num_layers=len(layout), sdxl_vae=self.tvae)
        x_hat = ((x_hat + 1) / 2).squeeze(0).permute(1, 0, 2, 3).float()
        size = image.size
        layers = [images[1].convert("RGBA").resize(size)]
        for i in range(2, x_hat.shape[0]):
            arr = (x_hat[i].permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
            layers.append(Image.fromarray(arr, "RGBA").resize(size))
        return layers


def make(log=print):
    from ..backends.decomposer import MethodRouter
    return MethodRouter({"cld": CldDecomposer(log)})
