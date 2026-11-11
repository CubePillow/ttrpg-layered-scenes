"""Self-test of layerproto/layer_edit.py with a fake editor (first seed returns an opaque scene, later seeds keep the alpha).

    fastsdcpu/env/Scripts/python.exe prototype/tools/test_layer_edit.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import Image  # noqa: E402

from layerproto.layer_edit import edit_layer_keep_alpha, transparent_share  # noqa: E402

layer = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
layer.paste(Image.new("RGBA", (16, 16), (200, 100, 50, 255)), (24, 24))


def fake(img, seed):
    if seed == 42:
        return Image.new("RGBA", img.size, (10, 10, 40, 255))          # opaque scene: alpha lost
    out = img.copy()
    out.paste(Image.new("RGBA", (16, 16), (60, 40, 20, 255)), (24, 24))  # darker object, same alpha
    return out


out, rep = edit_layer_keep_alpha(fake, layer)
assert rep["accepted"] and len(rep["tries"]) == 2 and rep["tries"][0]["ok"] is False, rep
assert abs(transparent_share(out) - transparent_share(layer)) < 0.01
out2, rep2 = edit_layer_keep_alpha(lambda i, s: Image.new("RGBA", i.size, (1, 2, 3, 255)), layer, seeds=(1, 2))
assert not rep2["accepted"] and len(rep2["tries"]) == 2
print("OK", rep, rep2["accepted"])
