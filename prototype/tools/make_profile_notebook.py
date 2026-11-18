r"""Builds the Kaggle notebook for one server profile (layerproto/serve/profiles.py); the library is layerproto/serve/notebook.py.

    python prototype/tools/make_profile_notebook.py --profile qwen-layered --mode bench
    cd prototype/kaggle/upload_profile_qwen-layered_bench && python -m kaggle.cli kernels push -p .      # runs it as a batch job

    --mode bench : load the profile once, run its fox & cottage cases (paths A and B) and save strips + results.json
                   (output: /kaggle/working/bench_<profile>/)
    --mode serve : load the profile and serve it behind a Cloudflare quick tunnel until it is idle for --idle minutes or told to stop.
                   The app builds and pushes this notebook itself ("Start" button); by hand, import the .ipynb in the Kaggle editor
                   (pushing it would start a run) and paste the printed `LAYERPROTO-CONNECT <url>|<token>` line into the app.

One profile per session: the two T4s hold one big model at a time and loading takes minutes (see docs/models/TEMPLATE.md).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.dirname(HERE)
sys.path.insert(0, PROTO)
from layerproto.serve import notebook  # noqa: E402
from layerproto.serve.profiles import PROFILES  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
ap.add_argument("--mode", default="bench", choices=["bench", "serve"])
ap.add_argument("--owner", default=os.environ.get("KAGGLE_USERNAME", "markandreduesing"), help="your Kaggle user name")
ap.add_argument("--idle", type=float, default=20, help="serve mode: stop after this many idle minutes")
a = ap.parse_args()
out = os.path.join(PROTO, "kaggle", f"upload_profile_{a.profile}_{a.mode}")
kid = notebook.build(a.profile, a.mode, out, a.owner, idle_minutes=a.idle)
print("wrote", out, kid)
