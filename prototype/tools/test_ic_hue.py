"""CPU test: IC-Light hue shift on the fox layer and restore_chroma variants (one IC-Light run, several post-processes).

    fastsdcpu/env/Scripts/python.exe prototype/tools/test_ic_hue.py
"""
import os
import sys
import time

import numpy as np
import torch
from PIL import Image
from skimage import color

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from layerproto.relight import ICLightFBC, restore_chroma  # noqa: E402

RL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kaggle", "results_reveallayer_fox_v15", "reveal_out", "gs1.0_st12", "fox_cottage")
S = 384
bg = Image.open(os.path.join(RL, "bg_rgba.png")).convert("RGBA").resize((S, S))
objs = [Image.open(os.path.join(RL, f"layer_{i}_rgba.png")).convert("RGBA").resize((S, S)) for i in range(4)]
fox = Image.open(os.path.join(RL, "layer_4_rgba.png")).convert("RGBA").resize((S, S))
scene = bg.copy()
for o in objs:
    scene.alpha_composite(o)
t = time.time()
rl = ICLightFBC(device="cpu", dtype=torch.float32)
print("load", round(time.time() - t), "s", flush=True)
t = time.time()
lit = rl.relight(fox, scene.convert("RGB"), "soft warm daylight from the left, storybook illustration", steps=8, size=S)
print("relight", round(time.time() - t), "s", flush=True)


def mean_lab(im):
    a = np.asarray(im.convert("RGBA"))
    m = a[..., 3] > 200
    lab = color.rgb2lab(a[..., :3] / 255.0)
    return lab[m].mean(0)


print("mean Lab (L, a, b): original", np.round(mean_lab(fox), 1), "relit", np.round(mean_lab(lit), 1))
tiles = [fox, lit]
for k in (0.5, 0.8):
    v = restore_chroma(lit, fox, k)
    print("keep", k, np.round(mean_lab(v), 1))
    tiles.append(v)
out = Image.new("RGB", (S * len(tiles), S))
for i, im in enumerate(tiles):
    c = scene.copy()
    c.alpha_composite(im)
    out.paste(c.convert("RGB"), (S * i, 0))
out.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "img", "iclight_hue_restore.jpg"), quality=90)
