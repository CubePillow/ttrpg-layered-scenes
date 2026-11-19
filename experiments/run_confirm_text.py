"""Text-only counterparts of the confirmation test (no input image, no ControlNet).

Usage: env\\Scripts\\python.exe run_confirm_text.py <E|F|G>
  E: SDXL-Turbo text-to-image, 4 steps, Guidance 1.0      (counterpart of blocks A and B)
  F: SD-Turbo text-to-image, 4 steps, Guidance 1.0        (counterpart of block C)
  G: neutral SD1.5 + LCM-LoRA text-to-image, 6 steps,
     Guidance 1.0, no ControlNet                          (counterpart of block D)
Same prompts (restructured scene text + style prefix) and same seeds 11, 42, 99.
"""
import gc
import json
import sys
import time
import traceback

from run_confirm import OUT, SEEDS
from run_tests import STYLES, make_settings, prompt_for


def run(block: str) -> None:
    from backend.lcm_text_to_image import LCMTextToImage
    from backend.models.lcmdiffusion_setting import DiffusionTask

    if block == "E":
        s, cfg = make_settings("p2"), "text_sdxlturbo"
    elif block == "F":
        s, cfg = make_settings("p1"), "text_sdturbo"
    else:
        s, cfg = make_settings("p3"), "text_lcmlora_neutral_6steps"
        s.lcm_lora.base_model_id = "stable-diffusion-v1-5/stable-diffusion-v1-5"
        s.controlnet = None                  # text only: no control image
        s.rebuild_controlnet_pipeline = False
        s.inference_steps = 6
    s.diffusion_task = DiffusionTask.text_to_image.value
    s.init_image = None

    t = LCMTextToImage()
    t.init("cpu", s)
    log = []
    for seed in SEEDS:
        s.seed = seed
        out_dir = OUT / block / f"seed{seed}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for style in STYLES:
            s.prompt = prompt_for(style)
            t0 = time.time()
            try:
                t.generate(s)[0].save(out_dir / f"{cfg}__{style}.png")
                log.append({"block": block, "seed": seed, "cfg": cfg, "style": style,
                            "secs": round(time.time() - t0, 1)})
                print(f"confirm{block} seed{seed} {cfg} {style} {log[-1]['secs']}s", flush=True)
            except Exception:
                traceback.print_exc()
            gc.collect()
    (OUT / f"log_{block}.json").write_text(json.dumps(log, indent=1))
    print("ALL DONE confirm", block, flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
