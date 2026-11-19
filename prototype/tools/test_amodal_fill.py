"""CPU test of Sam2Decomposer._complete (no models): the hidden part of an object's box gets filled, its own pixels stay."""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from layerproto.backends.sam2_decomposer import Sam2Decomposer

dec = Sam2Decomposer.__new__(Sam2Decomposer)                  # skip model loading
dec._fill_hidden = lambda base, hidden, prompt, seed=5: Image.new("RGB", base.size, (10, 200, 10))
H = W = 64
bg = Image.new("RGBA", (W, H), (0, 0, 255, 255))
m_back = np.zeros((H, W), bool); m_back[10:40, 10:30] = True   # object visible only left of the covering object
m_front = np.zeros((H, W), bool); m_front[10:40, 30:50] = True
L = Image.new("RGBA", (W, H), (200, 0, 0, 255)); L.putalpha(Image.fromarray((m_back * 255).astype(np.uint8)))
out = dec._complete(bg, L, [("back", m_back), ("front", m_front)], 0, [[10, 10, 50, 40], [30, 10, 50, 40]], W, H)
a = np.asarray(out)
assert a[20, 20, 3] == 255 and tuple(a[20, 20, :3]) == (200, 0, 0), "own pixels must stay"
assert a[20, 40, 3] == 255 and tuple(a[20, 40, :3]) == (10, 200, 10), "hidden part must be filled"
assert a[50, 5, 3] == 0, "outside the box stays transparent"
print("amodal fill test passed")
