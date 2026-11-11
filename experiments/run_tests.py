"""Style-agnostic layout tests for the three FastSD CPU paths.

Usage: env\\Scripts\\python.exe run_tests.py <prep|p1|p2|p3>

Content text is identical for every run; only the style prefix changes, so the
results show how well each path (a) follows the sketch layout and (b) still
lets the prompt decide the style.
"""
import gc
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # folder that holds fastsdcpu/ and experiments/
APP = ROOT / "fastsdcpu"
sys.path.insert(0, str(APP / "src"))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

EXP = ROOT / "experiments"
INPUTS = EXP / "inputs"
SKETCH = INPUTS / "sketch_original.png"

CONTENT = (
    "one skeleton dancing next to a large campfire with a stone ring, "
    "campfire in the center, skeleton on the right side, "
    "night forest of tall pine trees, full moon and stars"
)
STYLES = {
    "pixelart": "pixel art, retro 16-bit game scene",
    "impressionist": "impressionist oil painting, visible brushstrokes, soft light",
    "hyperreal": "hyperrealistic photograph, ultra detailed, cinematic lighting",
    "nostyle": "",
}
SEED = 123123
SIZE = 512


def prompt_for(style_key: str) -> str:
    style = STYLES[style_key]
    return f"{style}, {CONTENT}" if style else CONTENT


def prep() -> None:
    from backend.annotators.image_control_factory import ImageControlFactory

    raw = Image.open(SKETCH).convert("RGBA")
    bg = Image.new("RGBA", raw.size, (255, 255, 255, 255))
    raw = Image.alpha_composite(bg, raw).convert("RGB").resize((SIZE, SIZE))
    raw.save(INPUTS / "init_raw.png")
    raw.filter(ImageFilter.GaussianBlur(8)).save(INPUTS / "init_blur.png")

    canny = ImageControlFactory().create_control("Canny").get_control_image(raw)
    canny.save(INPUTS / "control_canny.png")

    # Scribble-style control: any non-white stroke becomes a white line on black
    arr = np.asarray(raw).astype(np.int16)
    strength = 255 - arr.min(axis=2)
    lines = (strength > 60).astype(np.uint8) * 255
    scribble = Image.fromarray(lines).filter(ImageFilter.MaxFilter(3)).convert("RGB")
    scribble.save(INPUTS / "control_scribble.png")
    print("prep done:", sorted(p.name for p in INPUTS.iterdir()))


def contact_sheet(out_dir: Path, configs: list[str], title: str) -> None:
    cell, label_h, side_w = 256, 22, 190
    cols = list(STYLES)
    sheet = Image.new(
        "RGB", (side_w + cell * len(cols), label_h + cell * len(configs)), "white"
    )
    d = ImageDraw.Draw(sheet)
    for c, style in enumerate(cols):
        d.text((side_w + c * cell + 4, 5), style, fill="black")
    for r, cfg in enumerate(configs):
        d.text((4, label_h + r * cell + 4), cfg, fill="black")
        for c, style in enumerate(cols):
            f = out_dir / f"{cfg}__{style}.png"
            if f.exists():
                im = Image.open(f).convert("RGB").resize((cell, cell))
                sheet.paste(im, (side_w + c * cell, label_h + r * cell))
    sheet.save(out_dir / f"_sheet_{title}.png")


def make_settings(path: str):
    from backend.models.lcmdiffusion_setting import (
        ControlNetSetting,
        DiffusionTask,
        LCMDiffusionSetting,
    )

    s = LCMDiffusionSetting()
    s.image_width = s.image_height = SIZE
    s.seed = SEED
    s.use_seed = True
    s.guidance_scale = 1.0
    s.inference_steps = 4
    s.negative_prompt = ""
    if path == "p1":
        s.lcm_model_id = "stabilityai/sd-turbo"
        s.diffusion_task = DiffusionTask.image_to_image.value
    elif path == "p2":
        s.lcm_model_id = "stabilityai/sdxl-turbo"
        s.diffusion_task = DiffusionTask.image_to_image.value
    elif path == "p3":
        s.use_lcm_lora = True
        s.lcm_lora.base_model_id = "Lykon/dreamshaper-8"
        s.lcm_lora.lcm_lora_id = "latent-consistency/lcm-lora-sdv1-5"
        s.diffusion_task = DiffusionTask.text_to_image.value
        s.controlnet = ControlNetSetting(
            adapter_path=str(
                APP / "controlnet_models" / "control_v11p_sd15_scribble_fp16.safetensors"
            ),
            conditioning_scale=0.8,
            enabled=True,
        )
        s.controlnet._control_image = Image.open(INPUTS / "control_scribble.png")
        s.rebuild_controlnet_pipeline = True
    return s


def run(path: str) -> None:
    from backend.lcm_text_to_image import LCMTextToImage

    s = make_settings(path)
    out_dir = EXP / path
    out_dir.mkdir(exist_ok=True)

    if path == "p1":
        configs = [
            (f"{init}_s{int(st*100)}", {"init": init, "strength": st})
            for init in ("raw", "blur")
            for st in (0.6, 0.8)
        ]
    elif path == "p2":
        configs = [
            ("raw_s80", {"init": "raw", "strength": 0.8}),
            ("blur_s80", {"init": "blur", "strength": 0.8}),
            ("blur_s60", {"init": "blur", "strength": 0.6}),
        ]
    else:
        configs = [
            (f"{ctl}_c{int(sc*100)}", {"ctl": ctl, "scale": sc})
            for ctl in ("canny", "scribble")
            for sc in (0.6, 1.0)
        ]

    if path in ("p1", "p2"):
        s.init_image = Image.open(INPUTS / "init_raw.png")  # init() resizes it
    t = LCMTextToImage()
    t.init("cpu", s)
    log = []
    for name, cfg in configs:
        if path == "p3":
            s.controlnet.conditioning_scale = cfg["scale"]
            s.controlnet._control_image = Image.open(INPUTS / f"control_{cfg['ctl']}.png")
        else:
            s.init_image = Image.open(INPUTS / f"init_{cfg['init']}.png")
            s.strength = cfg["strength"]
        for style in STYLES:
            s.prompt = prompt_for(style)
            t0 = time.time()
            try:
                img = t.generate(s)[0]
                img.save(out_dir / f"{name}__{style}.png")
                log.append({"cfg": name, "style": style, "secs": round(time.time() - t0, 1)})
                print(f"{path} {name} {style} {log[-1]['secs']}s", flush=True)
            except Exception:
                traceback.print_exc()
                log.append({"cfg": name, "style": style, "error": True})
            gc.collect()
        contact_sheet(out_dir, [c[0] for c in configs], path)
    (out_dir / "log.json").write_text(json.dumps(log, indent=1))
    print("ALL DONE", path, flush=True)


if __name__ == "__main__":
    INPUTS.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1]
    if mode == "prep":
        prep()
    else:
        run(mode)
