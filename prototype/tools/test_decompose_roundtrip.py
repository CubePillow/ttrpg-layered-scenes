"""Local check of the image -> layers integration without a GPU: fake decomposer behind the real FastAPI route,
RemoteDecomposer client over an in-process transport, Engine.decompose_image -> scene.json -> compose.

    fastsdcpu/env/Scripts/python.exe prototype/tools/test_decompose_roundtrip.py
"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fastapi.testclient import TestClient
from PIL import Image
import requests

from layerproto.backends import decomposer as D
from layerproto.config import Settings
from layerproto.engine import Engine
from layerproto.remote_server import build_app
from layerproto.scene import Scene, new_scene_id


def fake(image, p):   # background = image, one object layer = the red box region
    bg = image.convert("RGBA")
    obj = Image.new("RGBA", image.size, (0, 0, 0, 0)); obj.paste(image.crop((100, 100, 300, 300)).convert("RGBA"), (100, 100))
    return [bg, obj]


client = TestClient(build_app(chain=type("C", (), {"info": lambda self: {}})(), token="t", decomposer=fake))
class _R:   # route requests.post through the TestClient
    def __init__(self, r): self.r = r
    def raise_for_status(self): self.r.raise_for_status()
    def json(self): return self.r.json()
D.requests = type("rq", (), {"post": staticmethod(lambda url, json=None, headers=None, timeout=None: _R(client.post(url.split("//", 1)[1].split("/", 1)[1].join(["/", ""]) if False else "/" + url.rsplit("/", 1)[1], json=json, headers=headers)))})
with tempfile.TemporaryDirectory() as td:
    os.environ["LAYERPROTO_URL"], os.environ["LAYERPROTO_TOKEN"] = "http://x", "t"   # the connection, not a setting
    s = Settings(); s.scenes_dir = td; s.width = s.height = 512
    eng = Engine(s)
    img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_scene", "fox_cottage.png")).convert("RGB")
    sc = Scene(id=new_scene_id("t"), user_input="fox & cottage")
    eng.decompose_image(sc, img, D.DecomposeParams(names=["patch"], method="fake"))
    assert [l.role for l in sc.layers] == ["background", "object"], sc.layers
    out = eng.compose(sc)
    diff = abs(__import__("numpy").asarray(out.convert("RGB"), dtype=int) - __import__("numpy").asarray(img.resize(out.size), dtype=int)).mean()
    reloaded = Scene.load(os.path.join(td, sc.id, "scene.json"))
    print("layers", [(l.name, l.role, l.current().mode) for l in reloaded.layers], "recomposite diff", round(float(diff), 2))
    assert diff < 1.0
print("OK")
