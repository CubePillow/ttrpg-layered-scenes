"""Builds the Kaggle notebook (and its kernel-metadata.json) for one server profile; used by the app and by the CLI.

    build("qwen21", "serve", out_dir, owner="someone", token=..., topic=..., run_id=..., idle_minutes=20)
    build("qwen21", "bench", out_dir, owner="someone")

  * bench: load the profile once, run its fox & cottage cases (paths A and B), save strips + results.json (/kaggle/working/bench_<profile>/)
  * serve: load the profile, then serve it behind a tunnel until it is idle or told to stop (serve/launch.py). Pushing this
           notebook with the Kaggle API starts it as a batch run: that is what the app does (layerproto/kaggle_launch.py).

Weights: the profile's `weights` notebooks (tools/make_weights_notebooks.py) are attached as kernel sources, so a session reads
them from /kaggle/input instead of downloading about 17.5 GB again.
"""
from __future__ import annotations

import base64
import io
import json
import os
import time
import zipfile

PROTO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEIGHTS_OWNER = os.environ.get("LAYERPROTO_WEIGHTS_OWNER", "markandreduesing")     # whose public weights notebooks to attach


def code_zip_b64(prof) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(os.path.join(PROTO, "layerproto")):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fn in files:
                if fn.endswith(".py"):
                    full = os.path.join(root, fn)
                    z.write(full, os.path.join("prototype", os.path.relpath(full, PROTO)))
        for rel, src in prof.files.items():          # extra images: 512 px JPEG data (the Kaggle API rejects notebooks of about 1.1 MB and more)
            from PIL import Image
            b = io.BytesIO()
            Image.open(os.path.join(os.path.dirname(PROTO), src)).convert("RGB").resize((512, 512)).save(b, "JPEG", quality=88)
            z.writestr(f"prototype/{rel}", b.getvalue())
        if prof.cases:
            for fn in ("fox_cottage.png", "fox_cottage.json"):
                z.write(os.path.join(PROTO, "test_scene", fn), f"prototype/test_scene/{fn}")
    return base64.b64encode(buf.getvalue()).decode()


def source(prof, mode: str, token: str = "", topic: str = "", run_id: str = "", idle_minutes: float = 20, max_minutes: float = 180) -> str:
    bench = f'''
from layerproto.serve import benchmark
res = benchmark.run_cases(dec, prof.cases, "/kaggle/working/bench_{prof.name}")
print("BENCH DONE", round(time.time() - _T0), "s since start", flush=True)
'''
    serve = f'''
from layerproto.serve import launch
launch.run(prof, dec, token={token!r}, topic={topic!r}, run_id={run_id!r}, idle_minutes={idle_minutes!r}, max_minutes={max_minutes!r})
'''
    cap = "signal.signal(signal.SIGALRM, _cap); signal.alarm(55 * 60)" if mode == "bench" else ""
    watcher = f"""
import threading, urllib.request, json as _json
_SINCE = {int(time.time()) - 5}
def _watch_stop():
    while True:
        try:
            _r = urllib.request.urlopen("https://ntfy.sh/{topic}/json?poll=1&since=" + str(_SINCE), timeout=20).read().decode()
            for _l in _r.splitlines():
                try:
                    if _json.loads(_json.loads(_l).get("message", "{{}}")).get("stop") == {run_id!r}:
                        print("STOP requested by the app", flush=True)
                        os._exit(0)
                except ValueError:
                    pass
        except Exception:
            pass
        _t.sleep(15)
threading.Thread(target=_watch_stop, daemon=True).start()
""" if (topic and run_id and mode == "serve") else ""
    return f'''
import signal, time as _t
_T0 = _t.time()
def _cap(*a): raise TimeoutError("55 min cap hit after %.0fs" % (_t.time() - _T0))
{cap}
import base64, io, zipfile, subprocess, sys, os, time, importlib
{watcher}
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ.update({json.dumps(prof.env)})
PIP = {json.dumps(prof.pip)}
os.environ["SAM2_BUILD_CUDA"] = "0"
for _grp in PIP:
    _r = subprocess.run([sys.executable, "-m", "pip", "-q", "install"] + _grp.split(), capture_output=True, text=True)
    print("pip", _grp, "rc", _r.returncode, flush=True)
subprocess.run([sys.executable, "-m", "pip", "-q", "install", "fastapi", "uvicorn"], capture_output=True)
os.makedirs("/kaggle/working/code", exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode("{code_zip_b64(prof)}"))).extractall("/kaggle/working/code")
sys.path.insert(0, "/kaggle/working/code/prototype")
from layerproto.serve.profiles import PROFILES
prof = PROFILES["{prof.name}"]
_mod, _fn = prof.factory.split(":")
t_load = time.time()
dec = getattr(importlib.import_module(_mod), _fn)()
print("PROFILE LOADED", prof.name, round(time.time() - t_load), "s", flush=True)
{bench if mode == "bench" else serve}
'''


def kernel_slug(prof, mode: str) -> str:
    return f"profile-{prof.name}-{mode}"


def build(profile: str, mode: str, out_dir: str, owner: str, token: str = "", topic: str = "", run_id: str = "",
          idle_minutes: float = 20, max_minutes: float = 180) -> str:
    """Write <out_dir>/<slug>.ipynb and kernel-metadata.json; return the kernel id `owner/slug`."""
    from .profiles import PROFILES
    prof = PROFILES[profile]
    os.makedirs(out_dir, exist_ok=True)
    src = source(prof, mode, token, topic, run_id, idle_minutes, max_minutes)
    compile(src, "cell", "exec")
    nb = {"cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src.strip("\n").splitlines(True)}],
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    slug = kernel_slug(prof, mode)
    json.dump(nb, open(os.path.join(out_dir, f"{slug}.ipynb"), "w", encoding="utf-8"), indent=1)
    sources = list(prof.kernel_sources) + [f"{WEIGHTS_OWNER}/{w}" for w in prof.weights]
    json.dump({"id": f"{owner}/{slug}", "title": slug, "code_file": f"{slug}.ipynb", "language": "python", "kernel_type": "notebook",
               "is_private": "true", "enable_gpu": "true", "enable_tpu": "false", "enable_internet": "true", "machine_shape": prof.gpu,
               "dataset_sources": [], "competition_sources": [], "kernel_sources": sources, "model_sources": []},
              open(os.path.join(out_dir, "kernel-metadata.json"), "w"), indent=1)
    return f"{owner}/{slug}"
