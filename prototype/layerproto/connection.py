"""Where the app finds its GPU servers (Kaggle notebooks behind tunnels), kept apart from the settings.

Two roles, one Kaggle notebook each (they rarely generate at the same time, and each fits a T4 pair alone):
  * "generate": SDXL-Turbo, text to image and image to image (profile `sdxl-turbo`)
  * "split":    Qwen-Image-2.1, image to layers and per-layer edits (profile `qwen21`, or any other decomposer profile)

Why a separate file: the connection (URL + token) changes every Kaggle session, the settings do not. When both lived in
`prototype/config.json`, the app read the file once at start-up, so editing the URL after the app was running and then pressing
**Save as default** wrote the OLD URL / token back over the new one, and an edit made after the app started was never seen. Now:

  * the connections are stored in `~/.layerproto/connection.json` (override the path with LAYERPROTO_CONNECTION_FILE),
    written only by `save()` (the app does it when it starts a notebook or when you paste a line) and always replaced atomically;
  * every request reads it again (`load()`), so the order "start the app, then start Kaggle, then connect" does not matter;
  * `config.json` never contains it; an old `remote_url` / `remote_token` in `config.json` is read as a fallback for "split";
  * the environment variables LAYERPROTO_URL / LAYERPROTO_TOKEN ("split") and LAYERPROTO_GEN_URL / LAYERPROTO_GEN_TOKEN
    ("generate") override everything (handy for scripts).

The app starts the notebooks itself and finds their URL automatically (layerproto/kaggle_launch.py); the notebooks also print one
line to paste by hand:  `LAYERPROTO-CONNECT https://....trycloudflare.com|<token>`.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import asdict, dataclass

import requests

PLACEHOLDER_URLS = ("", "http://127.0.0.1:8765")        # the old default of Settings.remote_url: not a real server
ROLES = ("generate", "split", "alt")      # alt: another splitter profile (Qwen-Image-Layered, SAM2, ...) started on demand
_ENV = {"split": ("LAYERPROTO_URL", "LAYERPROTO_TOKEN"), "generate": ("LAYERPROTO_GEN_URL", "LAYERPROTO_GEN_TOKEN"),
        "alt": ("LAYERPROTO_ALT_URL", "LAYERPROTO_ALT_TOKEN")}


def path() -> str:
    return os.environ.get("LAYERPROTO_CONNECTION_FILE") or os.path.join(os.path.expanduser("~"), ".layerproto", "connection.json")


@dataclass
class Connection:
    url: str = ""
    token: str = ""
    profile: str = ""          # which model profile the server runs
    updated: float = 0.0

    @property
    def configured(self) -> bool:
        return self.url not in PLACEHOLDER_URLS


def _legacy() -> Connection | None:
    """remote_url / remote_token from an old prototype/config.json (read only; never written again)."""
    cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    try:
        d = json.load(open(cfg, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    url = str(d.get("remote_url", "")).strip()
    return Connection(url, str(d.get("remote_token", ""))) if url not in PLACEHOLDER_URLS else None


def _read() -> dict:
    """{role: {url, token, profile, updated}} from the file (an old flat file counts as the "split" server)."""
    try:
        d = json.load(open(path(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(d, dict):
        return {}
    if "servers" in d and isinstance(d["servers"], dict):
        return {k: v for k, v in d["servers"].items() if isinstance(v, dict)}
    return {"split": d} if d.get("url") else {}


def load(role: str = "split") -> Connection:
    """The current connection of a role: environment, then the connection file, then (split only) a legacy config.json."""
    uenv, tenv = _ENV[role]
    url = os.environ.get(uenv, "").strip()
    if url:
        return Connection(url.rstrip("/"), os.environ.get(tenv, ""))
    d = _read().get(role)
    if d:
        c = Connection(str(d.get("url", "")).rstrip("/"), str(d.get("token", "")), str(d.get("profile", "")), float(d.get("updated", 0) or 0))
        if c.configured:
            return c
    return (_legacy() if role == "split" else None) or Connection()


def _write(servers: dict) -> None:
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"servers": servers}, f, indent=2)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def save(url: str, token: str = "", profile: str = "", role: str = "split") -> Connection:
    """Store one role's connection, keeping the other roles; written atomically (temp file in the same folder, then replace)."""
    c = Connection(url.strip().rstrip("/"), token.strip(), profile, time.time())
    servers = _read()
    servers[role] = asdict(c)
    _write(servers)
    return c


def clear(role: str | None = None) -> None:
    """Forget one role (or all of them)."""
    if role is None:
        try:
            os.remove(path())
        except OSError:
            pass
        return
    servers = _read()
    if servers.pop(role, None) is not None:
        _write(servers)


_URL = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")


def parse(text: str) -> tuple[str, str]:
    """Pull (url, token) out of whatever was pasted: the notebook's one-liner, `url|token`, `url token`, or the JSON block
    (`{"remote_url": ..., "remote_token": ...}`) the older notebooks printed. Raises ValueError if no URL is found."""
    text = (text or "").strip()
    if not text:
        raise ValueError("nothing pasted")
    try:                                                      # the JSON block
        d = json.loads(text[text.index("{"):text.rindex("}") + 1])
        url = str(d.get("remote_url") or d.get("url") or "").strip()
        if url:
            return url.rstrip("/"), str(d.get("remote_token") or d.get("token") or "").strip()
    except ValueError:
        pass
    line = next((l for l in text.splitlines() if "LAYERPROTO-CONNECT" in l), text.splitlines()[-1] if "|" in text else text)
    line = line.replace("LAYERPROTO-CONNECT", "").strip()
    m = _URL.search(line)
    if not m:
        raise ValueError("no http(s) URL found in what was pasted")
    url = m.group(0)
    rest = (line[:m.start()] + " " + line[m.end():]).strip(" |\t\r\n")
    token = rest.split()[0] if rest else ""
    if "|" in url:                                           # url|token with the pipe glued to the URL
        url, _, tail = url.partition("|")
        token = token or tail
    return url.rstrip("/"), token.strip("| ")


def check(url: str | None = None, token: str | None = None, timeout: float = 12.0, role: str = "split") -> dict:
    """Ask the server's /health: {"ok": True, "info": {...}} or {"ok": False, "error": "..."}."""
    if url is None:
        c = load(role)
        url, token = c.url, c.token
    if url in PLACEHOLDER_URLS:
        return {"ok": False, "error": "not connected: start the server (or paste the connection line of the Kaggle notebook)"}
    try:
        r = requests.get(f"{url.rstrip('/')}/health", headers={"X-Token": token} if token else {}, timeout=timeout)
        if r.status_code == 401:
            return {"ok": False, "error": "the server rejected the token (a new Kaggle session has a new token)"}
        r.raise_for_status()
        return {"ok": True, "info": r.json()}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"cannot reach {url} ({type(e).__name__}); the Kaggle notebook may have stopped or the URL changed"}
