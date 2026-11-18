"""Confirmation test, see CONFIRMATION_TEST_PLAN.md.

Usage: env\\Scripts\\python.exe run_confirm.py <A|B|C|D>
Blocks A and B share one SDXL pipeline run, so run `A` (it also does B).
"""
import gc
import json
import sys
import time
import traceback

from run_tests import EXP, INPUTS, STYLES, make_settings, prompt_for
from PIL import Image

SEEDS = [11, 42, 99]
OUT = EXP / "confirm"


def run(block: str) -> None:
    from backend.lcm_text_to_image import LCMTextToImage

    if block == "A":      # P2: filled 0.7/0.8/0.9 (block A) and raw 0.8 (block B)
        s = make_settings("p2")
        jobs = [("A", "filled", v) for v in (0.7, 0.8, 0.9)] + [("B", "raw", 0.8)]
        s.init_image = Image.open(INPUTS / "init_filled.png")
    elif block == "C":    # P1: filled 0.7/0.8
        s = make_settings("p1")
        jobs = [("C", "filled", v) for v in (0.7, 0.8)]
        s.init_image = Image.open(INPUTS / "init_filled.png")
    else:                 # D: P3 neutral base, canny of the plain sketch, 6 steps
        s = make_settings("p3")
        s.lcm_lora.base_model_id = "stable-diffusion-v1-5/stable-diffusion-v1-5"
        s.controlnet._control_image = Image.open(INPUTS / "control_canny.png")
        s.controlnet.conditioning_scale = 0.7
        s.inference_steps = 6
        jobs = [("D", "canny-raw", 0.7)]

    t = LCMTextToImage()
    t.init("cpu", s)
    log = []
    for seed in SEEDS:
        s.seed = seed
        for blk, inp, val in jobs:
            if block == "D":
                cfg = "neutral_g10_c70_6steps"
            else:
                cfg = f"{inp}_s{int(val * 100)}"
                s.strength = val
                s.init_image = Image.open(INPUTS / f"init_{inp}.png")
            out_dir = OUT / blk / f"seed{seed}"
            out_dir.mkdir(parents=True, exist_ok=True)
            for style in STYLES:
                s.prompt = prompt_for(style)
                t0 = time.time()
                try:
                    t.generate(s)[0].save(out_dir / f"{cfg}__{style}.png")
                    log.append({"block": blk, "seed": seed, "cfg": cfg, "style": style,
                                "secs": round(time.time() - t0, 1)})
                    print(f"confirm{blk} seed{seed} {cfg} {style} {log[-1]['secs']}s", flush=True)
                except Exception:
                    traceback.print_exc()
                gc.collect()
    (OUT / f"log_{block}.json").write_text(json.dumps(log, indent=1))
    print("ALL DONE confirm", block, flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
