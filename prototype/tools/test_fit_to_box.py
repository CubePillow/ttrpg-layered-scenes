"""CPU test of Engine.fit_layer_to_box: the visible content ends up inside the planned box, centred, aspect kept."""
import os, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from layerproto.config import Settings
from layerproto.engine import Engine
from layerproto.scene import Scene, Layer, Variant

tmp = tempfile.mkdtemp()
s = Settings(); s.scenes_dir = tmp; s.width = s.height = 200
eng = Engine.__new__(Engine); eng.s = s
sc = Scene(id="t", user_input="", refined_prompt="", n_layers=1)
img = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); img.paste((255, 0, 0, 255), (20, 40, 60, 100))      # 40 x 60 object, top left
os.makedirs(sc.folder(tmp), exist_ok=True); img.save(f"{sc.folder(tmp)}/a.png")
L = Layer(id="o1", name="obj", role="object", depth=1, prompt="x"); L.box = [0.5, 0.5, 0.4, 0.4]
L.variants = [Variant(file="a.png", seed=0, prompt="x")]; L.selected = 0
sc.layers = [L]
eng.fit_layer_to_box(sc, "o1")
out = eng._placed(Image.open(f"{sc.folder(tmp)}/a.png"), L, 200, 200)
bb = out.split()[-1].point(lambda a: 255 if a > 40 else 0).getbbox()
cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
assert abs(cx - 140) < 3 and abs(cy - 140) < 3, (bb, cx, cy)                    # box centre (0.7, 0.7) of 200 px
assert bb[3] - bb[1] <= 80 + 2 and bb[2] - bb[0] <= 80 + 2, bb                  # fits the 80 px box
assert abs((bb[3] - bb[1]) - 80) < 3, bb                                        # taller side fills the box
print("fit_to_box test passed:", bb)
