"""Server routes (generate / split / edit / shutdown / idle), the Kaggle launcher hand-shake and the notebook builder, with fakes.

No GPU, no network, no Kaggle: requests go through FastAPI's TestClient, `_kaggle` and the ntfy read are stubbed.
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
tmp = tempfile.mkdtemp()
os.environ["LAYERPROTO_CONNECTION_FILE"] = os.path.join(tmp, "connection.json")
os.environ["LAYERPROTO_LAUNCHER_FILE"] = os.path.join(tmp, "launcher.json")
os.environ["KAGGLE_USERNAME"] = "tester"
for k in ("LAYERPROTO_URL", "LAYERPROTO_TOKEN", "LAYERPROTO_GEN_URL", "LAYERPROTO_GEN_TOKEN"):
    os.environ.pop(k, None)

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from layerproto import connection, kaggle_launch  # noqa: E402
from layerproto.backends import client  # noqa: E402
from layerproto.backends.decomposer import DecomposeParams, MethodRouter  # noqa: E402
from layerproto.backends.remote import b64_to_img, img_to_b64  # noqa: E402
from layerproto.config import Settings  # noqa: E402
from layerproto.engine import Engine  # noqa: E402
from layerproto.remote_server import build_app  # noqa: E402
from layerproto.scene import Scene  # noqa: E402


class FakeGen:
    def txt2img(self, prompt, seed, steps, size, negative):
        return Image.new("RGB", (size, size), (200, 30 + seed % 200, 30))

    def img2img(self, image, prompt, strength, seed, steps, size, negative):
        return Image.new("RGB", (size, size), (30, 30, 200))


def fake_split(image, p):
    bg = Image.new("RGBA", image.size, (90, 140, 90, 255))
    objs = []
    for i, _ in enumerate(p.names):
        o = Image.new("RGBA", image.size, (0, 0, 0, 0))
        o.paste((200, 50 + 40 * i, 50, 255), (60 + 90 * i, 150, 140 + 90 * i, 300))
        objs.append(o)
    return [bg] + objs


def fake_editor(layer, prompt, seed):
    out = layer.copy()
    out.paste((10, 10, 10, 255), (0, 0, 20, 20))
    return out, {"accepted": True, "tries": [{"seed": seed, "ok": True}]}


stopped = []
gen_app = build_app(None, "gtok", generator=FakeGen(), profile="sdxl-turbo", idle_minutes=20, on_shutdown=lambda: stopped.append("gen"))
split_app = build_app(None, "stok", decomposer=MethodRouter({"qwen21-extract": fake_split}), editor=fake_editor, profile="qwen21", idle_minutes=20)
G, SP = TestClient(gen_app), TestClient(split_app)

# 1. roles, token, idle time, routes present only where they belong
assert G.get("/health").status_code == 401
h = G.get("/health", headers={"X-Token": "gtok"}).json()
assert h["role"] == "generate" and h["profile"] == "sdxl-turbo" and h["idle_limit_minutes"] == 20
assert SP.get("/health", headers={"X-Token": "stok"}).json()["role"] == "split"
assert G.post("/decompose", json={}, headers={"X-Token": "gtok"}).status_code == 404
assert SP.post("/txt2img", json={"prompt": "x"}, headers={"X-Token": "stok"}).status_code == 404
time.sleep(1.2)
G.get("/health", headers={"X-Token": "gtok"})
assert gen_app.state.idle_seconds() >= 1.0, "/health must not count as activity"
G.post("/txt2img", json={"prompt": "x"}, headers={"X-Token": "gtok"})
assert gen_app.state.idle_seconds() < 1.0, "a real request resets the idle clock"

# 2. the client talks to both servers through the stored connections; the engine uses them
def fake_post(role, route, payload, timeout=900):
    app_client, tok = (G, "gtok") if role == "generate" else (SP, "stok")
    if not connection.load(role).configured:
        raise client.NotConnected(f"Not connected to the {role} server.")
    r = app_client.post(route, json=payload, headers={"X-Token": tok})
    assert r.status_code == 200, r.text
    return r.json()


client._post = fake_post
eng = Engine(Settings(scenes_dir=os.path.join(tmp, "scenes"), width=512, height=512))
try:
    eng.first_image("a fox")
    raise AssertionError("must say it is not connected")
except client.NotConnected as e:
    assert "generate" in str(e)
connection.save("http://gen", "gtok", "sdxl-turbo", role="generate")
connection.save("http://spl", "stok", "qwen21", role="split")
pic = eng.first_image("a fox", seed=5)
assert pic.size == (512, 512)
assert eng.first_image("night", init=pic, strength=0.5).getpixel((5, 5))[2] == 200

# 3. split -> layers -> edit one layer -> variants -> compose; only the edited layer changes
import layerproto.engine as engine_mod  # noqa: E402

class DirectDecomposer:                                  # RemoteDecomposer without HTTP
    def decompose(self, image, p):
        return fake_split(image, p)


engine_mod.RemoteDecomposer = lambda url, token: DirectDecomposer()
sc = Scene(id="t1", user_input="fox", refined_prompt="fox")
eng.decompose_image(sc, pic, DecomposeParams(method="qwen21-extract", names=["cottage", "fox"]))
assert [l.name for l in sc.layers] == ["background", "cottage", "fox"]
before = {l.id: len(l.variants) for l in sc.layers}
eng.edit_layer(sc, "fox", "make it white", seed=7)
after = {l.id: len(l.variants) for l in sc.layers}
assert after["fox"] == before["fox"] + 1 and after["cottage"] == before["cottage"], (before, after)
assert sc.layer("fox").current().mode == "edit" and sc.layer("fox").selected == 1
eng.compose(sc)

# 4. shutdown route calls the hook (after a short delay)
assert G.post("/shutdown", headers={"X-Token": "gtok"}).json()["ok"]
time.sleep(1.6)
assert stopped == ["gen"]

# 5. the notebook builder: compiles, carries the token / topic / run id, attaches the weights notebooks
from layerproto.serve import notebook  # noqa: E402

out = os.path.join(tmp, "nb")
kid = notebook.build("qwen21", "serve", out, "tester", token="TOK123", topic="topic-abc", run_id="run42", idle_minutes=7)
assert kid == "tester/profile-qwen21-serve"
meta = json.load(open(os.path.join(out, "kernel-metadata.json")))
assert meta["enable_gpu"] == "true" and meta["is_private"] == "true" and meta["enable_internet"] == "true"
assert [s.split("/")[1] for s in meta["kernel_sources"]] == ["weights-qwen21-text-encoder", "weights-qwen21-parts"], meta["kernel_sources"]
nb_src = "".join(json.load(open(os.path.join(out, "profile-qwen21-serve.ipynb")))["cells"][0]["source"])
assert "launch.run(prof, dec" in nb_src and "'TOK123'" in nb_src and "'topic-abc'" in nb_src and "'run42'" in nb_src and "idle_minutes=7" in nb_src
assert "signal.alarm" not in nb_src, "a serve notebook must not carry the 55 minute benchmark cap"
notebook.build("sdxl-turbo", "serve", os.path.join(tmp, "nb2"), "tester")
assert json.load(open(os.path.join(tmp, "nb2", "kernel-metadata.json")))["kernel_sources"][0].endswith("weights-sdxl-turbo")

# 6. launcher hand-shake: start pushes, poll finds the announcement and stores the connection, stop shuts down and forgets
connection.clear()
pushed = []


class R:
    def __init__(self, rc=0, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def fake_kaggle(*args, timeout=180):
    if args[:2] == ("kernels", "push"):
        pushed.append(json.load(open(os.path.join(args[3], "kernel-metadata.json")))["id"])
        return R(0, "Kernel version 1 successfully pushed.")
    if args[:2] == ("kernels", "status"):
        return R(0, f'{args[2]} has status "KernelWorkerStatus.RUNNING"')
    return R(0, "kaggle 2.2.5")


kaggle_launch._kaggle = fake_kaggle
ok, who = kaggle_launch.available()
assert ok and who == "tester"
print(kaggle_launch.start("split"))
assert pushed == ["tester/profile-qwen21-serve"]
run = json.load(open(kaggle_launch.state_path()))["runs"]["split"]
assert kaggle_launch.poll("split").startswith("starting")
kaggle_launch._announcement = lambda r: {"run": r["run"], "url": "http://spl", "role": "split", "profile": "qwen21"}
real_check = connection.check
connection.check = lambda url=None, token=None, timeout=12.0, role="split": (
    {"ok": True, "info": {"role": "split", "idle_seconds": 0, "idle_limit_minutes": 20}} if (url or connection.load(role).url) else {"ok": False, "error": "x"})
assert kaggle_launch.poll("split") == "ready"
c = connection.load("split")
assert c.url == "http://spl" and c.token == run["token"] and c.profile == "qwen21"
assert not connection.load("generate").configured
connection.check = real_check
# the token that went into the notebook is the one the app stored; it never appears in the ntfy message
assert "token" not in json.dumps({"run": run["run"], "url": "http://spl"})
posted = []
import requests  # noqa: E402

requests.post = lambda url, data=None, headers=None, timeout=0: (posted.append(url), type("Resp", (), {"raise_for_status": lambda self: None})())[1]
assert "shutting down" in kaggle_launch.stop("split") and [u for u in posted if u.endswith("/shutdown")] == ["http://spl/shutdown"]
assert not connection.load("split").configured and "split" not in json.load(open(kaggle_launch.state_path())).get("runs", {})
print("servers test passed")

# 7. launch.run end to end with a fake tunnel: announces once, serves, then ends by itself when idle
from layerproto.serve import launch  # noqa: E402
from layerproto.serve.profiles import PROFILES  # noqa: E402

announced = []
launch.open_tunnel = lambda port=launch.PORT, timeout=90: (type("P", (), {"terminate": lambda self: None})(), f"http://127.0.0.1:{port}")
launch.announce = lambda topic, payload, tries=5: announced.append((topic, payload)) or True
t0 = time.time()
launch.run(PROFILES["sdxl-turbo"], FakeGen(), token="tk", topic="tp", run_id="r1", idle_minutes=0.02, max_minutes=1, poll=0.3)
assert announced and announced[0][1]["run"] == "r1" and announced[0][1]["role"] == "generate" and "tk" not in json.dumps(announced[0][1])
assert time.time() - t0 < 20, "the idle watchdog must end the process"
print("launch test passed")

# 8. studio: one server with both roles, one notebook with the three weights notebooks, one Start for both connections
both_app = build_app(None, "btok", decomposer=MethodRouter({"qwen21-extract": fake_split}), editor=fake_editor, generator=FakeGen(),
                     profile="studio", idle_minutes=20)
B = TestClient(both_app)
assert B.get("/health", headers={"X-Token": "btok"}).json()["role"] == "both"
assert B.post("/txt2img", json={"prompt": "x"}, headers={"X-Token": "btok"}).status_code == 200
assert B.post("/edit", json={"image": img_to_b64(Image.new("RGBA", (64, 64))), "prompt": "x"}, headers={"X-Token": "btok"}).status_code == 200
nb3 = os.path.join(tmp, "nb3")
assert notebook.build("studio", "serve", nb3, "tester", token="T", topic="tp", run_id="r") == "tester/profile-studio-serve"
assert [s.split("/")[1] for s in json.load(open(os.path.join(nb3, "kernel-metadata.json")))["kernel_sources"]] == [
    "weights-qwen21-text-encoder", "weights-qwen21-parts", "weights-sdxl-turbo"]
connection.clear()
pushed.clear()
kaggle_launch._announcement = lambda r: {"run": r["run"], "url": "http://both", "role": "both", "profile": "studio"}
connection.check = lambda url=None, token=None, timeout=12.0, role="split": (
    {"ok": True, "info": {"role": "both"}} if (url or connection.load(role).url) else {"ok": False, "error": "x"})
print(kaggle_launch.start("both"))
assert pushed == ["tester/profile-studio-serve"]
assert kaggle_launch.poll("both") == "ready"
assert connection.load("generate").url == "http://both" and connection.load("split").url == "http://both"
assert connection.load("generate").token == connection.load("split").token
posted.clear()
assert "shutting down" in kaggle_launch.stop("both") and [u for u in posted if u.endswith("/shutdown")] == ["http://both/shutdown"]
assert not connection.load("generate").configured and not connection.load("split").configured
print("studio test passed")
