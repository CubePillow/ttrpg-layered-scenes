"""Connects the backend to the Kaggle GPU session, using the prototype's launcher (prototype/layerproto/kaggle_launch.py).

When the backend starts it signs in, joins a session that is already running, or starts a new one, and then waits until the
models are loaded. Every step is written to the backend log and is available to the frontend.

A running session uses the weekly Kaggle GPU quota. It stops by itself after IDLE_MINUTES without requests.
Set KAGGLE_AUTO_CONNECT=0 to start the backend without connecting.

    GET  /api/kaggle/status    the current step, progress and log
    POST /api/kaggle/connect   connect now
    POST /api/kaggle/stop      end the Kaggle session
"""
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger("uvicorn.error")

PROTOTYPE_DIR = Path(__file__).resolve().parent.parent / "prototype"
ROLE = "both"  # SDXL-Turbo and Qwen-Image-2.1 in one Kaggle session
IDLE_MINUTES = 20
POLL_SECONDS = 15
WATCH_SECONDS = 60
EXPECTED_START_SECONDS = 11 * 60  # Only used to estimate the progress bar
MAX_LOG_LINES = 60

_lock = threading.Lock()
_worker: threading.Thread | None = None
_cancel = threading.Event()
_status = {
    "stage": "off",  # off, account, notebook, session, ready, stopping, failed
    "progress": 0,
    "message": "Not connected to Kaggle.",
    "username": None,
    "started_at": None,
    "log": [],
}


def _load_launcher():
    if str(PROTOTYPE_DIR) not in sys.path:
        sys.path.insert(0, str(PROTOTYPE_DIR))
    from layerproto import kaggle_launch

    return kaggle_launch


def _update(stage: str, message: str, progress: int | None = None, **fields) -> None:
    """Records a step. A message is only logged when it changes."""
    with _lock:
        changed = message != _status["message"] or stage != _status["stage"]
        _status.update(stage=stage, message=message, **fields)
        if progress is not None:
            _status["progress"] = progress
        if changed:
            stamp = datetime.now().strftime("%H:%M:%S")
            _status["log"] = [*_status["log"], f"{stamp} {message}"][-MAX_LOG_LINES:]
    if changed:
        logger.log(logging.ERROR if stage == "failed" else logging.INFO, "[kaggle] %s", message)


def _session_started(launcher) -> float:
    run = launcher._load_state().get("runs", {}).get(ROLE) or {}
    return float(run.get("started") or time.time())


def _wait_until_ready(launcher) -> bool:
    started = _session_started(launcher)
    stamp = datetime.fromtimestamp(started, timezone.utc).isoformat(timespec="seconds")
    while not _cancel.is_set():
        state = launcher.poll(ROLE)
        if state == "ready":
            return True
        if state == "off" or state.startswith("failed"):
            _update("failed", state.removeprefix("failed: "))
            return False
        share = min((time.time() - started) / EXPECTED_START_SECONDS, 1)
        _update("session", state.removeprefix("starting: ").capitalize(), 20 + int(share * 75), started_at=stamp)
        _cancel.wait(POLL_SECONDS)
    return False


def _models_ready(launcher) -> bool:
    """100% means both models answer: SDXL-Turbo makes pictures, Qwen-Image-2.1 splits and edits them."""
    checks = [launcher.connection.check(role=role) for role in ("generate", "split")]
    return all(check["ok"] and check["info"].get("role") == "both" for check in checks)


def _watch_session(launcher) -> None:
    while not _cancel.wait(WATCH_SECONDS):
        if launcher.poll(ROLE) != "ready":
            _update("off", "The Kaggle session has ended.", 0)
            return


def _connect() -> None:
    try:
        _update("account", "Checking the Kaggle account...", 5)
        launcher = _load_launcher()
        ok, detail = launcher.available()
        if not ok:
            _update("failed", detail, 0)
            return
        _update("notebook", f"Signed in as {detail}. Looking for a running session...", 10, username=detail)
        if launcher.poll(ROLE) != "ready":
            _update("notebook", "Sending the notebook to Kaggle...", 15)
            _update("notebook", launcher.start(ROLE, IDLE_MINUTES), 20)
            if not _wait_until_ready(launcher):
                return
        _update("session", "Checking SDXL-Turbo and Qwen-Image-2.1...", 97)
        if not _models_ready(launcher):
            _update("failed", "The Kaggle session answers, but the two models are not ready.")
            return
        _update("ready", "Connected. SDXL-Turbo and Qwen-Image-2.1 are ready to use.", 100)
        _watch_session(launcher)
    except Exception as error:  # A failed connection must never stop the backend
        logger.exception("[kaggle] Connection failed")
        _update("failed", f"Could not connect to Kaggle: {error}")


def connect() -> None:
    """Connects in the background, so the backend is ready at once."""
    global _worker
    with _lock:
        if _worker and _worker.is_alive():
            return
        _cancel.clear()
        _worker = threading.Thread(target=_connect, daemon=True)
        _worker.start()


def auto_connect() -> None:
    if os.environ.get("KAGGLE_AUTO_CONNECT", "1") != "0":
        connect()
    else:
        logger.info("[kaggle] Automatic connection is turned off.")


def _stop() -> None:
    try:
        worker = _worker
        if worker and worker is not threading.current_thread():
            worker.join(timeout=20)
        _update("off", _load_launcher().stop(ROLE), 0, started_at=None)
    except Exception as error:
        logger.exception("[kaggle] Stopping failed")
        _update("failed", f"Could not stop the Kaggle session: {error}")


router = APIRouter(prefix="/api/kaggle", tags=["kaggle"])


@router.get("/status")
def get_status():
    with _lock:
        return dict(_status)


@router.post("/connect", status_code=202)
def connect_now():
    connect()
    return get_status()


@router.post("/stop", status_code=202)
def stop_session():
    _cancel.set()
    _update("stopping", "Stopping the Kaggle session...")
    threading.Thread(target=_stop, daemon=True).start()
    return get_status()
