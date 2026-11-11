"""Profile `reveallayer`: RevealLayer (image + boxes -> RGBA layers incl. hidden parts and a filled background) on two T4s; method `reveallayer`.

Moved out of tools/make_reveallayer_trial.py (the code that produced run 15: 512 px, 140 s at 12 steps / 334 s at 16 steps with true_gs 3.5):
  * FLUX.1-dev GGUF Q4_K_S re-classed into RevealLayer's custom transformer, the repo's bundled diffusers 0.34, fp16 patches
    (mask fill -1e4, guarded refiner residual, fp32 VAE decode), the ViT-B/32 weights path rewritten for Kaggle
  * fp16_mixed + a guard hook that replaces non-finite fp16 activations, text encoders split over the two GPUs
  * the transformer is offloaded to the CPU before the fp32 decode and moved back for the next request
FLUX.1-dev Non-Commercial licence applies. `DecomposeParams.guidance` is RevealLayer's `true_gs` (1.0 skips the negative pass: half the time).
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time
from types import SimpleNamespace

from PIL import Image

from ..backends.decomposer import DecomposeParams

PIP = ["transformers==4.57.1 gguf>=0.10 peft==0.15.2 mmengine==0.10.7 einops sentencepiece protobuf"]
ENV = {"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
RL = "/kaggle/working/RevealLayer"
COMMIT = "da68ff58889a1799a1e75efd23e72bccebbf7589"


def _sh(cmd):
    print("$", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


def _patch(path, old, new):
    p = f"{RL}/{path}"
    s = open(p, encoding="utf-8").read()
    assert old in s, f"patch anchor not found in {path}: {old[:60]}"
    open(p, "w", encoding="utf-8").write(s.replace(old, new))


def setup():
    """Clone RevealLayer at the tested commit and apply the T4 / fp16 patches (idempotent per fresh clone)."""
    if os.path.exists(RL):
        return
    _sh(f"git clone https://github.com/360CVGroup/RevealLayer {RL} && cd {RL} && git checkout {COMMIT}")
    _patch("infer.py", "torch.bfloat16", "torch.float16")
    _patch("infer.py", "resolution=1024,", "resolution=512,")
    _patch("infer.py", "guidance_scale=args.cfg,", "guidance_scale=args.cfg, true_gs=getattr(args,'true_gs',3.5),")
    _patch("models/custom_model_mmdit.py", "-1e9, dtype=dtype", "torch.finfo(dtype).min, dtype=dtype")
    _patch("models/custom_pipeline.py", "neg_noise_pred = self.transformer(", "neg_noise_pred = noise_pred if true_gs == 1.0 else self.transformer(")
    os.makedirs("/kaggle/working/vit32", exist_ok=True)
    _sh("wget -q -nc -O /kaggle/working/vit32/vit_b_32-d86f8d99.pth https://download.pytorch.org/models/vit_b_32-d86f8d99.pth")
    _sh("mkdir -p /home/jovyan/boomcheng-work-shcdt/zhaoshihao/pretrained_model/vit32 && cp /kaggle/working/vit32/vit_b_32-d86f8d99.pth "
        "/home/jovyan/boomcheng-work-shcdt/zhaoshihao/pretrained_model/vit32/")
    for f in glob.glob(RL + "/**/*.py", recursive=True):
        s = open(f, encoding="utf-8", errors="ignore").read()
        if "vit32" in s and "/home/jovyan" in s:
            open(f, "w", encoding="utf-8").write(re.sub(r"/home/jovyan/[^'\"]*?vit32", "/kaggle/working/vit32", s))
    _patch("models/custom_model_mmdit.py", "torch.full((t_total, t_total), torch.finfo(dtype).min, dtype=dtype", "torch.full((t_total, t_total), -1e4, dtype=dtype")
    _patch("models/custom_model_mmdit.py", "hidden_states_part2 = hidden_states[:, l0_len:, :] + delta",
           "hidden_states_part2 = (hidden_states[:, l0_len:, :].float() + torch.nan_to_num(delta.float(), nan=0.0, posinf=6e4, neginf=-6e4)).clamp(-6e4, 6e4).to(hidden_states.dtype)")
    _patch("models/custom_pipeline.py", "image_segs = [self.vae.decode(latents_seg, return_dict=False)[0] for latents_seg in latents_segs]",
           "image_segs = [self.vae.float().decode(latents_seg.float(), return_dict=False)[0] for latents_seg in latents_segs]")


class RevealLayerDecomposer:
    def __init__(self, log=print):
        setup()
        sys.path[:0] = [RL, f"{RL}/diffusers/src"]                  # the repo's bundled diffusers 0.34 (GGUF + mask-aware Flux blocks)
        for m in [k for k in sys.modules if k.startswith("diffusers")]:
            del sys.modules[m]
        import torch
        import torch.nn as nn
        from diffusers import AutoencoderKL, FlowMatchEulerDiscreteScheduler, FluxTransformer2DModel, GGUFQuantizationConfig
        from huggingface_hub import hf_hub_download, snapshot_download
        from safetensors.torch import load_file

        from ..fp16_mixed import apply_fp16_mixed
        from models.adapter import HybridRefiner
        from models.custom_model_mmdit import CustomFluxTransformer2DModel
        from models.custom_model_xvae import AutoencoderKLTransformerTraining as CustomVAE
        from models.custom_pipeline import CustomFluxPipelineCfg
        import infer

        t0 = time.time()
        self.torch, self.log, self.infer = torch, log, infer
        self.D0, self.D1, dt = torch.device("cuda:0"), torch.device("cuda:1"), torch.float16
        D0, D1 = self.D0, self.D1
        gguf = hf_hub_download("city96/FLUX.1-dev-gguf", "flux1-dev-Q4_K_S.gguf")
        ck = snapshot_download("qihoo360/RevealLayer", allow_patterns=["*.pt", "*.safetensors", "xvae/*"])
        base = snapshot_download("ostris/Flex.1-alpha", allow_patterns=["model_index.json", "text_encoder/*", "text_encoder_2/*", "tokenizer/*",
                                                                        "tokenizer_2/*", "vae/*", "scheduler/*"])
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
        t.register_to_config(max_layer_num=12)
        t.max_layer_num = 12
        t.layer_pe = nn.Parameter(torch.load(f"{ck}/layer_pe.pt", map_location="cpu").to(dt).view(1, 12, 1, 1, 3072))
        t.refiner = HybridRefiner(feature_dim=3072, pixel_dim=16, time_emb_dim=3072, attn_hidden=1024, num_layers=1, patch_size=2)
        t.refiner.load_state_dict(torch.load(f"{ck}/Refiner.pt", map_location="cpu"), strict=False)
        t.refiner.to(dt)
        t.to(D0).eval()
        apply_fp16_mixed(t)
        self.hits = {"n": 0}

        def guard(mod, inp, out):
            def fix(o):
                if torch.is_tensor(o) and o.dtype == torch.float16 and not torch.isfinite(o).all():
                    self.hits["n"] += 1
                    return torch.nan_to_num(o, nan=0.0, posinf=6e4, neginf=-6e4)
                return o
            return tuple(fix(o) for o in out) if isinstance(out, tuple) else fix(out)
        for b in list(t.transformer_blocks) + list(t.single_transformer_blocks) + [t.refiner]:
            b.register_forward_hook(guard)
        vae = AutoencoderKL.from_pretrained(base, subfolder="vae", torch_dtype=dt)
        pipe = CustomFluxPipelineCfg.from_pretrained(base, transformer=t, vae=vae, scheduler=sched, torch_dtype=dt)
        pipe.vae.to(D0)
        pipe.text_encoder.to(D0)
        pipe.text_encoder_2.to(D1)
        CustomFluxPipelineCfg._execution_device = property(lambda self: D0)
        orig_enc = pipe.encode_prompt

        def enc(*a, device=None, **kw):
            pipe.text_encoder.to(D1)
            out = orig_enc(*a, device=D1, **kw)
            pipe.text_encoder.to(D0)
            return tuple(o.to(D0) if torch.is_tensor(o) else o for o in out)
        pipe.encode_prompt = enc
        lora = {k.replace("transformer.module.", "transformer."): v for k, v in load_file(f"{ck}/pytorch_lora_weights.safetensors").items()}
        pipe.load_lora_weights(lora, adapter_name="layer")
        for n, p in pipe.transformer.named_parameters():
            if "lora_" in n:
                p.data = p.data.to(D0, dt)
        tvae = CustomVAE()
        tvae.load_state_dict(torch.load(f"{ck}/xvae/transparent_decoder_ckpt.pth", map_location="cpu"), strict=False)
        tvae.to(D0).eval()

        def to32(m, args, kwargs):
            c = lambda x: x.float() if torch.is_tensor(x) and x.is_floating_point() else x
            return tuple(c(a) for a in args), {k: c(v) for k, v in kwargs.items()}
        tvae.float().register_forward_pre_hook(to32, with_kwargs=True)
        for sub in tvae.modules():
            if sub is not tvae and hasattr(sub, "decode"):
                sub.register_forward_pre_hook(to32, with_kwargs=True)
        od = tvae.decode
        tvae.decode = lambda *a, **k: od(*[x.float() if torch.is_tensor(x) and x.is_floating_point() else x for x in a], **k)
        pipe.vae.float()
        for name in ("encode", "decode"):
            f = getattr(pipe.vae, name)
            setattr(pipe.vae, name, (lambda f: lambda *a, **k: f(*[x.float() if torch.is_tensor(x) and x.is_floating_point() else x for x in a], **k))(f))
        pipe.vae.enable_slicing()
        for v in (pipe.vae, tvae):
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
        if p.method != "reveallayer":
            raise ValueError(f"unknown method {p.method!r}; this profile offers ['reveallayer']")
        if not p.boxes:
            raise ValueError("reveallayer needs boxes (one [x0, y0, x1, y1] per object, back to front, in input pixels)")
        torch = self.torch
        work = "/kaggle/working/reveal_req"
        os.makedirs(work, exist_ok=True)
        path = f"{work}/input.png"
        image.convert("RGB").resize((512, 512)).save(path)
        sample = {"index": "req", "layout": [list(b) for b in p.boxes], "full_image_path": path}
        out_dir = f"{work}/out"
        args = SimpleNamespace(seed=p.seed or 43, cfg=1.0, steps=p.steps, true_gs=float(p.guidance), output_dir=out_dir)
        self.t.to(self.D0)
        torch.cuda.empty_cache()
        with torch.inference_mode():
            self.infer.test_one_sample(args, sample, self.pipe, self.tvae, self.D0, shuffle=False)
        d = glob.glob(f"{out_dir}/**/bg_rgba.png", recursive=True)
        if not d:
            raise RuntimeError("RevealLayer produced no output")
        d = os.path.dirname(d[0])
        size = image.size
        layers = [Image.open(f"{d}/bg_rgba.png").convert("RGBA").resize(size)]
        for i in range(len(p.boxes)):
            layers.append(Image.open(f"{d}/layer_{i}_rgba.png").convert("RGBA").resize(size))
        return layers


def make(log=print):
    from ..backends.decomposer import MethodRouter
    return MethodRouter({"reveallayer": RevealLayerDecomposer(log)})
