"""Live check of one Kaggle server through the app's own launcher (uses GPU quota of your Kaggle account).

    python prototype/tools/live_check.py generate      # SDXL-Turbo: start, wait, make a picture, stop
    python prototype/tools/live_check.py split         # Qwen-Image-2.1: start, wait, split + edit one layer, stop
    python prototype/tools/live_check.py both          # studio: both models in one session; pictures, split, edit, pictures again, GPU memory

Prints the status every 20 s, the seconds each step took, and always asks the server to shut down at the end.
Pictures are written to the folder given with --out (default: a temp folder).
"""
import argparse
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import Image  # noqa: E402

from layerproto import connection, kaggle_launch  # noqa: E402
from layerproto.backends import client  # noqa: E402
from layerproto.backends.decomposer import DecomposeParams, RemoteDecomposer  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("role", choices=["both", "generate", "split"])
ap.add_argument("--out", default=tempfile.mkdtemp(prefix="live_check_"))
ap.add_argument("--timeout-min", type=float, default=30)
ap.add_argument("--idle-minutes", type=float, default=10)
ap.add_argument("--attach", action="store_true", help="do not start a server, wait for the one already recorded by the launcher")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

ok, who = kaggle_launch.available()
print("kaggle:", ok, who, flush=True)
t0 = time.time()
print("attaching to the recorded run" if a.attach else kaggle_launch.start(a.role, idle_minutes=a.idle_minutes, force=True), flush=True)
try:
    state = ""
    while time.time() - t0 < a.timeout_min * 60:
        state = kaggle_launch.poll(a.role)
        print(f"[{time.time() - t0:5.0f}s] {state}", flush=True)
        if state == "ready" or state.startswith("failed"):
            break
        time.sleep(20)
    if state != "ready":
        raise SystemExit(f"not ready: {state}")
    chk = "split" if a.role == "both" else a.role
    print(f"READY after {time.time() - t0:.0f} s; health:", connection.check(role=chk)["info"], flush=True)
    if a.role in ("generate", "both"):
        for i, (steps, seed) in enumerate(((4, 13), (4, 13), (1, 5))):
            t = time.time()
            im = client.txt2img("storybook illustration of a thatched stone cottage, a big tree on the right, a red fox on the path", seed=seed, steps=steps)
            print(f"txt2img steps={steps} seed={seed}: {time.time() - t:.1f} s (first call includes the tunnel round trip)", flush=True)
            im.save(os.path.join(a.out, f"t2i_{i}.png"))
        t = time.time()
        client.img2img(im, "at night, moonlight", strength=0.5).save(os.path.join(a.out, "i2i.png"))
        print(f"img2img: {time.time() - t:.1f} s", flush=True)
    if a.role in ("split", "both"):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_scene", "fox_cottage.png")
        img = Image.open(src).convert("RGB")
        t = time.time()
        c = connection.load("split")
        layers = RemoteDecomposer(c.url, c.token).decompose(img, DecomposeParams(method="qwen21-extract", names=["cottage", "red fox"], resolution=512))
        print(f"split into {len(layers)} layers: {time.time() - t:.0f} s", flush=True)
        for i, L in enumerate(layers):
            L.save(os.path.join(a.out, f"layer_{i}.png"))
        t = time.time()
        out, report = client.edit_layer(layers[-1].resize((512, 512)), "This fox is white")
        out.save(os.path.join(a.out, "fox_white.png"))
        print(f"edit: {time.time() - t:.0f} s, report {report}", flush=True)
        if a.role == "both":                                   # the shared GPUs after Qwen has run: does SDXL-Turbo still fit?
            for i in range(2):
                t = time.time()
                client.txt2img("a red fox in a meadow, storybook illustration", seed=13 + i, steps=4).save(os.path.join(a.out, f"t2i_after_{i}.png"))
                print(f"txt2img after the Qwen run: {time.time() - t:.1f} s", flush=True)
            print("health after:", connection.check(role=chk)["info"], flush=True)
finally:
    print(kaggle_launch.stop(a.role), flush=True)
    print("pictures in", a.out)
