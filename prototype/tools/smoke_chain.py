"""Smoke test of the LayerDiffuse SDXL scene-to-layer chain: background -> blend -> extract.

Usage (from the repository root):
    fastsdcpu\\env\\Scripts\\python.exe prototype\\tools\\smoke_chain.py --steps 4 --guidance 1
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image  # noqa: E402
from layerproto.backends.layerdiffuse_chain import LayerDiffuseChain  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--model", default="stabilityai/sdxl-turbo")
p.add_argument("--scene", default="night forest clearing with tall pine trees under a starry sky, full moon, pixel art")
p.add_argument("--element", default="a skeleton dancing next to a campfire, pixel art")
p.add_argument("--steps", type=int, default=4)
p.add_argument("--guidance", type=float, default=1.0)
p.add_argument("--seed", type=int, default=7)
p.add_argument("--tag", default="turbo")
p.add_argument("--scene-image", default="", help="use this image as the scene instead of generating one")
p.add_argument("--size", type=int, default=512)
p.add_argument("--negative", default="")
a = p.parse_args()

out = os.path.join(HERE, "..", "scenes", "_chain")
os.makedirs(out, exist_ok=True)
c = LayerDiffuseChain(model=a.model)
S = dict(w=a.size, h=a.size, steps=a.steps, guidance=a.guidance, negative=a.negative)
t = time.time()
bg = (Image.open(a.scene_image).convert("RGBA").resize((a.size, a.size)) if a.scene_image
      else c.background(a.scene, a.seed, **S))
print(f"background {time.time() - t:.0f}s (incl. load {c.load_seconds:.0f}s)", flush=True); bg.save(f"{out}/{a.tag}_0_bg.png")
t = time.time(); ble = c.blend(bg, a.element, a.seed, **S)
print(f"blend {time.time() - t:.0f}s", flush=True); ble.save(f"{out}/{a.tag}_1_blend.png")
t = time.time(); fg = c.extract(bg, ble, a.element, a.seed, **S)
print(f"extract {time.time() - t:.0f}s", flush=True); fg.save(f"{out}/{a.tag}_2_layer.png")
hist = fg.split()[-1].histogram()
print("layer transparent %:", round(100 * sum(hist[:10]) / sum(hist), 1))
comp = bg.copy(); comp.alpha_composite(fg); comp.save(f"{out}/{a.tag}_3_recomposed.png")
grid = Image.new("RGBA", (2048, 512), (40, 160, 60, 255))
for i, im in enumerate([bg, ble, fg, comp]):
    tile = Image.new("RGBA", (512, 512), (40, 160, 60, 255)); tile.alpha_composite(im.resize((512, 512)))
    grid.paste(tile, (i * 512, 0))
grid.resize((1024, 256)).save(f"{out}/{a.tag}_grid.png")
print("saved", os.path.abspath(out))
