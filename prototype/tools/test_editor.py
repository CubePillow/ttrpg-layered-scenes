"""Backend of the canvas editor and the several-versions flow, with fakes (no GPU, no network).

Covers: editor API (scene, save with a cut-out layer, selected), rotation in the composite, first_images / split_versions /
edit_versions with seeds, the Stop message through ntfy, and that the serve notebook carries the stop watcher.
"""
import base64
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
tmp = tempfile.mkdtemp()
os.environ["LAYERPROTO_CONNECTION_FILE"] = os.path.join(tmp, "connection.json")
os.environ["LAYERPROTO_LAUNCHER_FILE"] = os.path.join(tmp, "launcher.json")
os.environ["KAGGLE_USERNAME"] = "tester"

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from layerproto import connection, editor_api, kaggle_launch  # noqa: E402
from layerproto.backends import client  # noqa: E402
from layerproto.backends.decomposer import DecomposeParams  # noqa: E402
from layerproto.config import Settings  # noqa: E402
from layerproto.engine import Engine  # noqa: E402
from layerproto.scene import Scene  # noqa: E402

eng = Engine(Settings(scenes_dir=os.path.join(tmp, "scenes"), width=256, height=256))

# 1. several versions: seeds count up; split versions add one variant per layer and run; edit versions add variants
seeds = []
client.txt2img = lambda prompt, seed=13, steps=4, size=512, negative="": seeds.append(seed) or Image.new("RGB", (size, size), (seed % 255, 0, 0))
client.img2img = lambda image, prompt, strength=0.5, seed=13, steps=4, size=512, negative="": seeds.append(("i2i", seed, strength)) or image
ims = eng.first_images("a fox", n=3, seed=10)
assert seeds == [10, 11, 12] and len(ims) == 3
sk = Image.new("RGB", (256, 256), "white")
eng.first_images("a fox", n=2, seed=5, init=sk, strength=0.8)
assert seeds[-2:] == [("i2i", 5, 0.8), ("i2i", 6, 0.8)]

calls = []


class FakeDec:
    def decompose(self, image, p):
        calls.append(p.seed)
        bg = Image.new("RGBA", image.size, (90, 140, 90, 255))
        o = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(o).rectangle([60, 80, 140, 200], fill=(200, 60, 50, 255))
        return [bg, o]


eng.decomposer_for = lambda role="split": FakeDec()
sc = Scene(id="s1", user_input="x")
eng.split_versions(sc, ims[0], DecomposeParams(method="qwen21-extract", names=["fox"]), versions=3)
assert calls == [0, 1, 2] and [len(l.variants) for l in sc.layers] == [3, 3]

client.edit_layer = lambda layer, prompt, seed=42: (layer.copy(), {"accepted": True, "tries": [{"seed": seed}]})
eng.edit_versions(sc, "fox", "white", versions=2, seed=42)
assert len(sc.layer("fox").variants) == 5 and sc.layer("fox").selected == 4

# 2. rotation and scale in the composite agree with the geometry: rotate 90 degrees about the visible centre
fox = sc.layer("fox")
fox.selected = 0
fox.rot = 90.0
sc.save(eng.s.scenes_dir)
out = eng.compose(sc, save=False)
assert out.getpixel((100, 90))[0] < 120, "the top of the original box must be empty after the rotation"   # 80x120 box -> 120x80 about (100, 140)
assert out.getpixel((150, 140))[0] > 150, "the rotated box now reaches x = 150"
fox.rot = 0.0

# 3. editor API: scene, save with a cut-out (new) layer, selected layer
app = FastAPI()
app.include_router(editor_api.make_router(eng))
C = TestClient(app)
d = C.get("/api/scene/s1").json()
assert [l["name"] for l in d["layers"]] == ["background", "fox"] and d["W"] == 256
assert C.get(d["layers"][1]["url"]).status_code == 200
assert C.get("/scenes/s1/../../x").status_code in (404, 400)
assert "layer editor" in C.get("/editor").text.lower()
buf = io.BytesIO()
cut = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
ImageDraw.Draw(cut).rectangle([10, 10, 50, 50], fill=(1, 2, 3, 255))
cut.save(buf, "PNG")
body = {"selected": "fox", "layers": [
    {"id": "background", "name": "background", "visible": True, "dx": 0, "dy": 0, "scale": 1, "rot": 0},
    {"id": "fox", "name": "fox", "visible": True, "dx": 0.1, "dy": 0.2, "scale": 1.5, "rot": 30},
    {"id": "new-1", "name": "Selection 1", "visible": True, "dx": 0, "dy": 0, "scale": 1, "rot": 0, "png": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}]}
r = C.post("/api/scene/s1/save", json=body).json()
assert [l["name"] for l in r["layers"]] == ["background", "fox", "Selection 1"] and r["layers"][2]["id"] != "new-1"
sc2 = Scene.load(os.path.join(eng.s.scenes_dir, "s1", "scene.json"))
assert sc2.layer("fox").dx == 0.1 and sc2.layer("fox").rot == 30 and sc2.layer("fox").scale == 1.5
assert sc2.layers[2].current().mode == "hand" and editor_api.selected("s1") == "fox"
C.post("/api/scene/s1/selected", json={"id": sc2.layers[2].id})
assert editor_api.selected("s1") == sc2.layers[2].id
body["layers"] = body["layers"][:2]                                 # a layer missing from the list is deleted
C.post("/api/scene/s1/save", json=body)
assert [l.name for l in Scene.load(os.path.join(eng.s.scenes_dir, "s1", "scene.json")).layers] == ["background", "fox"]

# 4. Stop: a ntfy stop message is sent even when no server answers yet (the session is still loading)
posted = []
import requests  # noqa: E402

requests.post = lambda url, data=None, headers=None, timeout=0: (posted.append((url, data)), type("R", (), {"raise_for_status": lambda self: None})())[1]
connection.clear()
kaggle_launch._save_state({"topic": "tp", "runs": {"both": {"run": "r9", "token": "t", "kernel": "u/k", "profile": "studio", "started": 1.0}}})
msg = kaggle_launch.stop("both")
assert "told to stop" in msg and posted and json.loads(posted[0][1]) == {"stop": "r9"} and posted[0][0].endswith("/tp"), (msg, posted)
assert "both" not in kaggle_launch._load_state()["runs"]

# 5. the serve notebook carries the stop watcher with the run id; the bench notebook does not
from layerproto.serve import notebook  # noqa: E402

notebook.build("studio", "serve", os.path.join(tmp, "nb"), "tester", token="T", topic="tp", run_id="r9")
src = "".join(json.load(open(os.path.join(tmp, "nb", "profile-studio-serve.ipynb")))["cells"][0]["source"])
assert "_watch_stop" in src and "'r9'" in src and "os._exit(0)" in src
notebook.build("qwen21", "bench", os.path.join(tmp, "nb2"), "tester")
assert "_watch_stop" not in "".join(json.load(open(os.path.join(tmp, "nb2", "profile-qwen21-bench.ipynb")))["cells"][0]["source"])
print("editor test passed")
