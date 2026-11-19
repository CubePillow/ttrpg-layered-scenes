"""Runs inside the Kaggle notebook: serve the loaded profile behind a Cloudflare quick tunnel, tell the app where it is, stop by itself.

    launch.run(prof, dec, token, topic="<ntfy topic>", run_id="<id>", idle_minutes=20, max_minutes=180)

  1. build the FastAPI app (layerproto/remote_server.py) for the profile's role and start uvicorn on 127.0.0.1:8765
  2. open a Cloudflare quick tunnel (URL and nothing else changes every session)
  3. announce the URL: one printed line `LAYERPROTO-CONNECT <url>|<token>` (copy by hand) AND, if a topic is given, one message
     `{"run": run_id, "role": ..., "profile": ..., "url": ...}` to https://ntfy.sh/<topic> that the app picks up
     (layerproto/kaggle_launch.py). The token is NOT in that message: the app generated it and put it into this notebook.
  4. watch the clock: the process ends when no authenticated request came for `idle_minutes`, after `max_minutes` in all, or when the
     app calls POST /shutdown. A pushed (batch) notebook then finishes and the GPU session is released.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import threading
import time
import urllib.request

PORT = 8765
CLOUDFLARED = "/kaggle/working/cloudflared"
CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"


def build(prof, dec, token: str, idle_minutes: float, on_shutdown):
    from ..remote_server import build_app
    if prof.kind == "generate":
        return build_app(None, token, generator=dec, profile=prof.name, idle_minutes=idle_minutes, on_shutdown=on_shutdown)
    if prof.kind == "both":
        return build_app(None, token, decomposer=dec, editor=getattr(dec, "editor", None), generator=getattr(dec, "generator", None),
                         profile=prof.name, idle_minutes=idle_minutes, on_shutdown=on_shutdown)
    return build_app(None, token, decomposer=dec, editor=getattr(dec, "editor", None), profile=prof.name,
                     idle_minutes=idle_minutes, on_shutdown=on_shutdown)


def open_tunnel(port: int = PORT, timeout: float = 90.0):
    """Start cloudflared; return (process, https URL)."""
    if not os.path.exists(CLOUDFLARED):
        urllib.request.urlretrieve(CLOUDFLARED_URL, CLOUDFLARED)
        os.chmod(CLOUDFLARED, 0o755)
    proc = subprocess.Popen([CLOUDFLARED, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t0 = time.time()
    for line in proc.stdout:
        m = re.search(r"https://[a-z0-9-]+[.]trycloudflare[.]com", line)
        if m:
            return proc, m.group(0)
        if time.time() - t0 > timeout:
            break
    proc.terminate()
    raise RuntimeError("the tunnel did not report a URL")


def announce(topic: str, payload: dict, tries: int = 5) -> bool:
    """Post to ntfy.sh (a public pub/sub service); the topic is a long random secret of the user, the token is not sent."""
    if not topic:
        return False
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=json.dumps(payload).encode(), method="POST",
                                 headers={"Title": "layerproto server ready", "Tags": "white_check_mark"})
    for i in range(tries):
        try:
            urllib.request.urlopen(req, timeout=15).read()
            return True
        except Exception as e:  # noqa: BLE001
            print("ntfy post failed:", e, flush=True)
            time.sleep(3 * (i + 1))
    return False


def run(prof, dec, token: str = "", topic: str = "", run_id: str = "", idle_minutes: float = 20, max_minutes: float = 180,
        poll: float = 15.0):
    import uvicorn

    token = token or secrets.token_urlsafe(16)
    server = None

    def stop():
        if server is not None:
            server.should_exit = True

    app = build(prof, dec, token, idle_minutes, stop)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    tunnel, url = open_tunnel()
    print("Server ready. Started from the app, nothing to do. By hand: copy the next line into the app (Connect box):")
    print(f"LAYERPROTO-CONNECT {url}|{token}", flush=True)
    role = {"generate": "generate", "both": "both"}.get(prof.kind, "split")
    announce(topic, {"run": run_id, "role": role, "profile": prof.name, "url": url})
    t0 = time.time()
    why = ""
    while not server.should_exit:
        time.sleep(poll)
        if idle_minutes and app.state.idle_seconds() > idle_minutes * 60:
            why = f"idle for {idle_minutes:g} minutes"
            break
        if max_minutes and time.time() - t0 > max_minutes * 60:
            why = f"{max_minutes:g} minute limit"
            break
    print("Stopping:", why or "shutdown requested", flush=True)
    server.should_exit = True
    time.sleep(2)
    tunnel.terminate()
