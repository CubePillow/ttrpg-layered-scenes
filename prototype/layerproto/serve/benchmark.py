"""Runs the fox & cottage benchmark cases (paths A and B) of a profile on an already loaded decomposer and saves strips + timings.

    run_cases(decomposer, PROFILES["qwen-layered"].cases, out_dir)

Per case: layers (PNG), recomposite, a strip (input | recomposite | layers) and `results.json` with the compute seconds of the last
repeat (the first repeat warms up), the layer count and the recomposite difference. Load time is not part of it (live-demo budget).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict

import numpy as np
from PIL import Image

from ..backends.decomposer import recomposite

SCENE = os.path.join(os.path.dirname(__file__), "..", "..", "test_scene", "fox_cottage.png")


def strip(inp, layers, tile=256):
    tiles = [inp, recomposite(layers).resize(inp.size)] + list(layers)
    S = Image.new("RGB", (tile * len(tiles), tile), (255, 255, 255))
    for i, im in enumerate(tiles):
        im = im.convert("RGBA").resize((tile, tile))
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255) if i < 2 else (200, 60, 200, 255))
        bg.alpha_composite(im)
        S.paste(bg.convert("RGB"), (tile * i, 0))
    return S


def run_cases(decomposer, cases, out_dir, scene=SCENE, log=print):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for c in cases:
        sp = os.path.join(os.path.dirname(scene), c.scene + ".png")
        inp = Image.open(sp).convert("RGB").resize((512, 512))
        row = dict(tag=c.tag, path=c.path, note=c.note, params=asdict(c.params))
        try:
            secs, layers = [], None
            for _ in range(c.repeats):
                t = time.time()
                layers = decomposer(inp, c.params)
                secs.append(round(time.time() - t, 1))
            comp = recomposite(layers).convert("RGB")
            diff = round(float(np.abs(np.asarray(comp, int) - np.asarray(inp, int)).mean()), 2)
            for i, L in enumerate(layers):
                L.save(f"{out_dir}/{c.tag}_layer{i}.png")
            comp.save(f"{out_dir}/{c.tag}_recomposite.png")
            strip(inp, layers).save(f"{out_dir}/{c.tag}_strip.jpg", quality=88)
            row.update(compute_s=secs[-1], all_runs_s=secs, layers=len(layers), recomposite_diff=diff)
        except Exception as e:  # noqa: BLE001 - one failing case must not stop the others
            import traceback
            traceback.print_exc()
            row.update(error=repr(e)[:300])
        log(json.dumps(row))
        results.append(row)
        json.dump(results, open(f"{out_dir}/results.json", "w"), indent=1)
    return results
