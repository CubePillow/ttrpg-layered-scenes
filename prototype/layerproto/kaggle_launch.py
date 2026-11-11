"""Start, find and stop the Kaggle GPU servers from the app, with the user's own Kaggle account.

    available()          -> (ok, why)             is the Kaggle API usable (package + credentials)?
    start("split")       -> push the serve notebook of profile qwen21 as a batch run (it loads, opens a tunnel, tells us where it is)
    start("generate")    -> the same for profile sdxl-turbo
    poll("split")        -> "starting" / "ready" / "off" / "failed: ..."; when the notebook has announced itself and answers /health,
                            the connection is stored (layerproto/connection.py) and the app uses it from the next request on
    stop("split")        -> POST /shutdown (the batch run ends, the GPU session is released) and forget the connection

How the app learns the tunnel URL (it changes every session): the notebook posts `{run, role, profile, url}` to
https://ntfy.sh/<topic> (a public pub/sub service) and the app reads it from there. The topic is a long random secret generated on
first use and kept in ~/.layerproto/launcher.json; the TOKEN never goes through ntfy (the app generates it and writes it into the
private notebook it pushes), so someone who learned the topic could only read a tunnel URL that needs the token. If ntfy.sh is
unreachable, paste the `LAYERPROTO-CONNECT` line from the notebook's output instead (Connect box).

Roles: "both" = profile `studio`, SDXL-Turbo and Qwen-Image-2.1 in ONE session (the default); "generate" / "split" = the same models in two separate sessions (Kaggle allows two GPU sessions at once). Servers stop by themselves after `idle_minutes` without a request.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

import requests

from . import connection

ROLE_PROFILE = {"both": "studio", "generate": "sdxl-turbo", "split": "qwen21"}
CONNECTS = {"both": ("generate", "split"), "generate": ("generate",), "split": ("split",), "alt": ("alt",)}      # connection roles a run serves
NTFY = os.environ.get("LAYERPROTO_NTFY", "https://ntfy.sh")
BOOT_TIMEOUT_MIN = 25          # pip + model load + tunnel; a cold Qwen-2.1 session without attached weights can take longer


def state_path() -> str:
    return os.environ.get("LAYERPROTO_LAUNCHER_FILE") or os.path.join(os.path.expanduser("~"), ".layerproto", "launcher.json")


def _load_state() -> dict:
    try:
        return json.load(open(state_path(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(d: dict) -> None:
    p = state_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, p)


def topic() -> str:
    d = _load_state()
    if not d.get("topic"):
        d["topic"] = "layerproto-" + secrets.token_urlsafe(24)
        _save_state(d)
    return d["topic"]


# ---------------------------------------------------------------------------------------------- Kaggle API
def _kaggle(*args: str, timeout: float = 180) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "kaggle.cli", *args], capture_output=True, text=True, timeout=timeout)


def username() -> str:
    if os.environ.get("KAGGLE_USERNAME"):
        return os.environ["KAGGLE_USERNAME"]
    for f in (os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json"),):
        try:
            return json.load(open(f, encoding="utf-8")).get("username", "")
        except (OSError, ValueError):
            pass
    try:
        for line in _kaggle("config", "view", timeout=30).stdout.splitlines():
            if line.strip().startswith("- username:"):
                return line.split(":", 1)[1].strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def available() -> tuple[bool, str]:
    """(True, user name) when the Kaggle CLI package and credentials are in place, else (False, what is missing)."""
    try:
        r = _kaggle("--version", timeout=30)
    except Exception as e:  # noqa: BLE001
        return False, f"the Kaggle package cannot be run ({type(e).__name__}); run: pip install kaggle"
    if r.returncode != 0:
        return False, "the Kaggle package is not installed; run: pip install kaggle"
    user = username()
    if not user:
        return False, "no Kaggle credentials; create a token at https://www.kaggle.com/settings (API) and save it as ~/.kaggle/kaggle.json or set KAGGLE_USERNAME / KAGGLE_KEY"
    return True, user


def _kernel_status(kid: str) -> str:
    out = (_kaggle("kernels", "status", kid, timeout=60).stdout or "")
    return out.split('"')[1].replace("KernelWorkerStatus.", "").lower() if '"' in out else "unknown"


# ---------------------------------------------------------------------------------------------- start / poll / stop
def start(role: str, idle_minutes: float = 20, force: bool = False, profile: str | None = None) -> str:
    """Push the serve notebook of the role's profile. Returns a message for the UI; raises RuntimeError on a hard failure."""
    from .serve import notebook
    ok, user = available()
    if not ok:
        raise RuntimeError(user)
    d = _load_state()
    cur = d.get("runs", {}).get(role)
    if cur and not force and time.time() - cur["started"] < BOOT_TIMEOUT_MIN * 60 and not _up(role):
        return f"{role} server is already starting (started {int((time.time() - cur['started']) / 60)} min ago)."
    if _up(role) and not force:
        return f"The {role} server is already running."
    run_id, token = secrets.token_hex(6), secrets.token_urlsafe(18)
    prof = profile or ROLE_PROFILE[role]            # role "alt": any decomposer profile (qwen-layered, sam2, reveallayer, cld ...)
    out = tempfile.mkdtemp(prefix="layerproto_nb_")
    try:
        kid = notebook.build(prof, "serve", out, user, token=token, topic=topic(), run_id=run_id, idle_minutes=idle_minutes)
        r = _kaggle("kernels", "push", "-p", out, timeout=300)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    text = (r.stdout + r.stderr).strip()
    if r.returncode != 0 or "successfully pushed" not in text:
        raise RuntimeError(f"Kaggle did not accept the notebook: {text[-400:]}")
    for r in CONNECTS[role]:
        connection.clear(r)                                  # an old session's URL is useless now
    d = _load_state()
    d.setdefault("runs", {})[role] = {"run": run_id, "token": token, "kernel": kid, "profile": prof, "started": time.time()}
    _save_state(d)
    return f"Started `{kid}` on Kaggle. Loading takes a few minutes (the first Qwen-Image-2.1 start is the longest)."


def _announcement(run: dict) -> dict | None:
    """The ntfy message of this run, if the notebook has posted it."""
    r = requests.get(f"{NTFY}/{topic()}/json", params={"poll": 1, "since": int(run["started"]) - 30}, timeout=15)
    r.raise_for_status()
    for line in r.text.splitlines():
        try:
            m = json.loads(json.loads(line).get("message", "{}"))
        except ValueError:
            continue
        if isinstance(m, dict) and m.get("run") == run["run"] and m.get("url"):
            return m
    return None


def _up(role: str) -> bool:
    """Do all connections this role serves answer /health?"""
    return all(connection.check(role=r)["ok"] for r in CONNECTS[role])


def poll(role: str) -> str:
    """One step of the hand-shake. Returns 'ready', 'off', 'starting: ...' or 'failed: ...'."""
    if _up(role):
        return "ready"
    run = _load_state().get("runs", {}).get(role)
    if not run:
        return "off"
    age = (time.time() - run["started"]) / 60
    try:
        msg = _announcement(run)
    except requests.exceptions.RequestException as e:
        msg = None
        note = f" (cannot read {NTFY}: {type(e).__name__}; paste the notebook's LAYERPROTO-CONNECT line instead)"
    else:
        note = ""
    if msg:
        for _ in range(12):                                   # the tunnel needs a few seconds before it answers
            if connection.check(msg["url"], run["token"], timeout=8)["ok"]:
                for r in CONNECTS[role]:
                    connection.save(msg["url"], run["token"], run["profile"], r)
                return "ready"
            time.sleep(5)
        return "starting: the server announced itself but does not answer yet"
    status = _kernel_status(run["kernel"])
    if status in ("error", "cancelacknowledged", "cancelled", "complete") and age > 1:
        return f"failed: the Kaggle notebook ended ({status}) before announcing itself. Open https://www.kaggle.com/code/{run['kernel']} and read its log"
    if age > BOOT_TIMEOUT_MIN:
        return f"failed: no sign of life after {BOOT_TIMEOUT_MIN} min (Kaggle status: {status}). See https://www.kaggle.com/code/{run['kernel']}"
    return f"starting: Kaggle status {status}, {age:.0f} min{note}"


def _ntfy_stop(run: dict) -> bool:
    """Tell the notebook to end its session: it watches the same ntfy topic, also while it is still loading."""
    try:
        requests.post(f"{NTFY}/{topic()}", data=json.dumps({"stop": run["run"]}), timeout=15).raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


def stop(role: str) -> str:
    """End the Kaggle session of this role in every state: a ntfy stop message (works while it is still loading), and /shutdown
    when the server already answers; then forget the connection."""
    run = _load_state().get("runs", {}).get(role)
    c = next((x for x in (connection.load(r) for r in CONNECTS[role]) if x.configured), connection.Connection())
    msg, done = "was not running", False
    if c.configured:                                          # a running server ends cleanly through its own route
        try:
            requests.post(f"{c.url}/shutdown", headers={"X-Token": c.token} if c.token else {}, timeout=15).raise_for_status()
            msg, done = "is shutting down", True
        except requests.exceptions.RequestException as e:
            msg = f"could not be reached ({type(e).__name__}); it ends by itself after its idle time"
    if not done and run and _ntfy_stop(run):                  # still loading (or not answering): the notebook's watcher ends the session
        msg = "was told to stop (a session that is still loading ends within about 15 seconds)"
    for r in CONNECTS[role]:
        connection.clear(r)
    d = _load_state()
    d.get("runs", {}).pop(role, None)
    _save_state(d)
    return f"The {role} server {msg}."
