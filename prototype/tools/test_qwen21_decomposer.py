"""CPU test of Qwen21Decomposer with a stub pipeline (no model)."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from layerproto.backends.decomposer import DecomposeParams
from layerproto.backends.qwen21_decomposer import Qwen21Decomposer, extract_prompt, background_prompt

class Out:  # stands in for the pipeline result
    def __init__(self, im): self.images = [im]

class StubPipe:
    _execution_device = "cpu"
    def __init__(self): self.prompts = []; self.n = 0
    def __call__(self, prompt, image, width, height, **k):
        self.prompts.append(prompt); self.n += 1
        if prompt.startswith("Remove"): return Out(image[0])
        if self.n == 2:                                   # first extract call returns an empty layer -> retried with the next seed
            return Out(Image.new("RGBA", (width, height), (0, 0, 0, 0)))
        a = np.zeros((height, width), np.uint8); a[20:60, 20:60] = 255
        im = Image.new("RGBA", (width, height), (200, 0, 0, 255)); im.putalpha(Image.fromarray(a)); return Out(im)

import torch
stub = StubPipe(); stub.__class__._execution_device = torch.device("cpu")
dec = Qwen21Decomposer(stub, size=128, seeds=(1, 2))
layers = dec(Image.new("RGB", (200, 160), (0, 0, 255)), DecomposeParams(names=["cottage", "red fox"], method="qwen21-extract"))
assert len(layers) == 3 and all(l.size == (200, 160) for l in layers)
assert np.asarray(layers[1].getchannel("A")).max() == 255, "empty first try must be retried"
assert "in front of it" in extract_prompt("cottage", ["fox"]) and "in front" not in extract_prompt("fox", [])
assert background_prompt(["a", "b"]).startswith("Remove the a, the b")
print("qwen21 decomposer test passed;", len(stub.prompts), "pipeline calls")
