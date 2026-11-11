"""CPU test: /methods advertises the loaded methods with the profile's presets, and RemoteDecomposer-side helper reads it."""
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fastapi.testclient import TestClient  # noqa: E402

from layerproto.backends import decomposer as D  # noqa: E402
from layerproto.remote_server import build_app  # noqa: E402

router = D.MethodRouter({"qwen-layered": lambda im, p: [im], "stable-layers": lambda im, p: [im], "qwen-lightning": lambda im, p: [im]})
client = TestClient(build_app(type("C", (), {"info": lambda s: {"backend": "x"}})(), "tok", decomposer=router, profile="qwen-layered"))
requests.get = lambda url, headers=None, timeout=None: client.get(url.replace("http://t", ""), headers=headers)
info = D.remote_methods("http://t", "tok")
assert info["profile"] == "qwen-layered", info
by = {m["method"]: m["presets"] for m in info["methods"]}
assert sorted(by) == ["qwen-layered", "qwen-lightning", "stable-layers"], by
assert [p["path"] for p in by["qwen-layered"]] == ["A", "B"], by["qwen-layered"]
assert by["stable-layers"][0]["params"]["sampler"] == "heun" and by["qwen-layered"][1]["params"]["resolution"] == 384
bad = client.get("/methods", headers={"X-Token": "wrong"})
assert bad.status_code == 401
print("methods route test passed:", {k: len(v) for k, v in by.items()})
