"""Smoke test: SDXL-Turbo + LayerDiffuse transparent LoRA on CPU.

Usage (from the repository root):
    fastsdcpu\\env\\Scripts\\python.exe prototype\\tools\\smoke_layerdiffuse.py --steps 4 --size 512
"""
import argparse
import os
import sys
import time

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vendor", "diffuser_layerdiffuse"))

import torch  # noqa: E402
from diffusers import StableDiffusionXLPipeline  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402
from safetensors.torch import load_file  # noqa: E402
from layer_diffuse.models import TransparentVAEDecoder  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--model", default="stabilityai/sdxl-turbo")
p.add_argument("--prompt", default="a white skeleton dancing, full body, pixel art")
p.add_argument("--steps", type=int, default=4)
p.add_argument("--size", type=int, default=512)
p.add_argument("--guidance", type=float, default=1.0)
p.add_argument("--seed", type=int, default=7)
p.add_argument("--out", default=os.path.join(HERE, "..", "scenes", "_smoke.png"))
a = p.parse_args()

t0 = time.time()
vae = TransparentVAEDecoder.from_pretrained(a.model, subfolder="vae", torch_dtype=torch.float32)
vae.set_transparent_decoder(load_file(hf_hub_download("LayerDiffusion/layerdiffusion-v1", "vae_transparent_decoder.safetensors")))
pipe = StableDiffusionXLPipeline.from_pretrained(a.model, vae=vae, torch_dtype=torch.float32, add_watermarker=False)
pipe.load_lora_weights("rootonchair/diffuser_layerdiffuse", weight_name="diffuser_layer_xl_transparent_attn.safetensors")
t1 = time.time()
print(f"load {t1 - t0:.1f}s", flush=True)
img = pipe(prompt=a.prompt, num_inference_steps=a.steps, guidance_scale=a.guidance, width=a.size, height=a.size,
           generator=torch.Generator("cpu").manual_seed(a.seed), return_dict=False)[0][0]
print(f"gen {time.time() - t1:.1f}s mode={img.mode} size={img.size}", flush=True)
os.makedirs(os.path.dirname(a.out), exist_ok=True)
img.save(a.out)
print("saved", os.path.abspath(a.out))
