"""Builds CPU-only Kaggle notebooks that download model weights into their saved output. Later GPU notebooks attach them as
kernel sources (/kaggle/input/<slug>/...), so a session reads the weights from disk instead of downloading them again
(Qwen-Image-2.1 alone is about 22.8 GB: 17.5 GB text encoder, 3.9 GB GGUF transformer, 1.4 GB VAE).

    python prototype/tools/make_weights_notebooks.py [--owner NAME] [--push]

The notebooks are private unless --public is given, and uncharged (no accelerator, so no GPU quota). Each output stays under Kaggle's ~20 GB per-notebook
limit, which is why Qwen-Image-2.1 is split in two. Run this once per Kaggle account that should own the weights; the others
attach the owner's public notebooks (layerproto/serve/notebook.py: WEIGHTS_OWNER, env LAYERPROTO_WEIGHTS_OWNER).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "kaggle")

NOTEBOOKS = {
    # Qwen-Image-Layered (older profiles)
    "qwen-layered-weights-transformer": """
import os, shutil, time
os.environ['HF_HUB_DISABLE_XET'] = '1'
from huggingface_hub import hf_hub_download
t = time.time()
p = hf_hub_download('unsloth/Qwen-Image-Layered-GGUF', 'qwen-image-layered-Q4_K_S.gguf', local_dir='/kaggle/working')
print(p, round(os.path.getsize(p) / 1e9, 2), 'GB in', round(time.time() - t), 's')
shutil.rmtree('/kaggle/working/.cache', ignore_errors=True)   # hf_hub_download metadata, not needed
print(os.listdir('/kaggle/working'))
""",
    "qwen-layered-weights-base": """
import os, shutil, time
os.environ['HF_HUB_DISABLE_XET'] = '1'
from huggingface_hub import snapshot_download
t = time.time()
d = snapshot_download('Qwen/Qwen-Image-Layered', local_dir='/kaggle/working/Qwen-Image-Layered',
                      allow_patterns=['model_index.json', 'text_encoder/*', 'vae/*', 'tokenizer/*', 'processor/*',
                                      'scheduler/*', 'transformer/config.json'])
shutil.rmtree('/kaggle/working/Qwen-Image-Layered/.cache', ignore_errors=True)
total = 0
for root, _, files in os.walk(d):
    for f in files:
        total += os.path.getsize(os.path.join(root, f))
print(d, round(total / 1e9, 2), 'GB in', round(time.time() - t), 's')
for sub in sorted(os.listdir(d)):
    print(' ', sub)
""",
    # Qwen-Image-2.1 (profile qwen21): text encoder + configs in one notebook, GGUF transformer + VAE in the other
    "weights-qwen21-text-encoder": """
import os, shutil, time
os.environ['HF_HUB_DISABLE_XET'] = '1'
from huggingface_hub import snapshot_download
t = time.time()
d = snapshot_download('Qwen/Qwen-Image-2.1-Turbo', local_dir='/kaggle/working/Qwen-Image-2.1-Turbo',
                      ignore_patterns=['transformer/*.safetensors', 'vae/*.safetensors', 'assets/*'])
shutil.rmtree(d + '/.cache', ignore_errors=True)
total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)
print(d, round(total / 1e9, 2), 'GB in', round(time.time() - t), 's')
print(sorted(os.listdir(d)))
""",
    "weights-qwen21-parts": """
import os, shutil, time
os.environ['HF_HUB_DISABLE_XET'] = '1'
from huggingface_hub import hf_hub_download, snapshot_download
t = time.time()
g = hf_hub_download('unsloth/Qwen-Image-2.1-Turbo-GGUF', 'qwen-image-2.1-turbo-Q4_K_S.gguf', local_dir='/kaggle/working')
v = snapshot_download('madebyollin/texture-fix-vae-for-qwen-image-2.1', local_dir='/kaggle/working/texture-fix-vae',
                      allow_patterns=['config.json', 'diffusion_pytorch_model.safetensors', 'LICENSE', 'NOTICE'])
shutil.rmtree('/kaggle/working/.cache', ignore_errors=True)
shutil.rmtree(v + '/.cache', ignore_errors=True)
print(g, round(os.path.getsize(g) / 1e9, 2), 'GB;', sorted(os.listdir(v)), 'in', round(time.time() - t), 's')
""",
    # SDXL-Turbo (profile sdxl-turbo): only the fp16 files
    "weights-sdxl-turbo": """
import os, shutil, time
os.environ['HF_HUB_DISABLE_XET'] = '1'
from huggingface_hub import snapshot_download
t = time.time()
d = snapshot_download('stabilityai/sdxl-turbo', local_dir='/kaggle/working/sdxl-turbo',
                      ignore_patterns=['*.onnx', '*.onnx_data', 'sd_xl_turbo_1.0*', '*.png', '*.jpg',
                                       'unet/diffusion_pytorch_model.safetensors', 'text_encoder/model.safetensors',
                                       'text_encoder_2/model.safetensors', 'vae/diffusion_pytorch_model.safetensors',
                                       'vae_decoder/*', 'vae_encoder/*'])
shutil.rmtree(d + '/.cache', ignore_errors=True)
total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)
print(d, round(total / 1e9, 2), 'GB in', round(time.time() - t), 's')
print(sorted(os.listdir(d)))
""",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default=os.environ.get("KAGGLE_USERNAME", "markandreduesing"), help="your Kaggle user name")
    ap.add_argument("--only", nargs="*", help="slugs to build (default: the Qwen-Image-2.1 and SDXL-Turbo ones)")
    ap.add_argument("--public", action="store_true", help="make the notebooks public so team members can attach them (default: private)")
    ap.add_argument("--push", action="store_true", help="run `kaggle kernels push` for each (starts a CPU run, no GPU quota)")
    a = ap.parse_args()
    slugs = a.only or ["weights-qwen21-text-encoder", "weights-qwen21-parts", "weights-sdxl-turbo"]
    for slug in slugs:
        src = NOTEBOOKS[slug]
        folder = os.path.join(OUT, "upload_" + slug)
        os.makedirs(folder, exist_ok=True)
        compile(src, slug, "exec")
        nb = {"cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                         "source": src.strip("\n").splitlines(True)}],
              "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                           "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
        json.dump(nb, open(os.path.join(folder, slug + ".ipynb"), "w", encoding="utf-8"), indent=1)
        json.dump({"id": f"{a.owner}/{slug}", "title": slug, "code_file": slug + ".ipynb", "language": "python",
                   "kernel_type": "notebook", "is_private": "false" if a.public else "true", "enable_gpu": "false", "enable_tpu": "false",
                   "enable_internet": "true", "machine_shape": "", "dataset_sources": [], "competition_sources": [],
                   "kernel_sources": [], "model_sources": []},
                  open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
        print("wrote", folder)
        if a.push:
            r = subprocess.run([sys.executable, "-m", "kaggle.cli", "kernels", "push", "-p", folder], capture_output=True, text=True)
            print((r.stdout + r.stderr).strip())


if __name__ == "__main__":
    main()
