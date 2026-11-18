r"""Generate candidates for the shared test scene (fox & cottage) with SDXL-Turbo on CPU.

    fastsdcpu\env\Scripts\python.exe prototype\tools\make_test_scene.py

Goal: one image that lends itself to layer splitting: a few clearly separated objects at different depths
(character in the centre, cottage behind it, a third object), clean foreground, clear ground contact.
"""
import os
import sys
import time

import torch
from diffusers import AutoPipelineForText2Image
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kaggle", "test_scene_candidates")
BASE = ("storybook illustration, a large red fox standing on open green lawn in the right foreground, "
        "a small stone cottage with an orange thatched roof in the middle distance, a low dry-stone wall with a "
        "wooden gate to the left of the cottage, a cobblestone path winding from the cottage into the foreground, "
        "a big leafy tree behind the cottage, a few small village houses on the rolling hills in the background, "
        "blue sky with soft clouds, {third}, clearly separated objects, soft daylight, painterly")
THIRDS = {"v2": "the fox stands alone on the lawn away from the wall and the path"}
SEEDS = [int(x) for x in sys.argv[1:]] or [11, 5, 8, 13, 17, 29]

pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float32)
outs = []
for name, third in THIRDS.items():
    for seed in SEEDS:
        t = time.time()
        im = pipe(prompt=BASE.format(third=third), num_inference_steps=4, guidance_scale=0.0, width=512, height=512,
                  generator=torch.Generator().manual_seed(seed)).images[0]
        f = os.path.join(OUT, f"A_{name}_s{seed}.png"); im.save(f); outs.append(f)
        print(os.path.basename(f), round(time.time() - t), "s", flush=True)
cols = 3; rows = (len(outs) + cols - 1) // cols
sheet = Image.new("RGB", (512 * cols, 512 * rows))
for i, f in enumerate(outs):
    sheet.paste(Image.open(f), ((i % cols) * 512, (i // cols) * 512))
sheet.save(os.path.join(OUT, f"A_variants_{list(THIRDS)[0]}.jpg"), quality=88)
print("done")
