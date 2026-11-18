import time

import pytest
from fastapi.testclient import TestClient

import kaggle_connection as kaggle
from main import app

client = TestClient(app)


class FakeLauncher:
    """Stands in for the prototype's launcher, so the tests never use the Kaggle quota."""

    def __init__(self, polls=("off", "starting: Kaggle status running, 1 min", "ready"), available=(True, "tester")):
        self.polls = list(polls)
        self.result = available
        self.started = 0
        self.stopped = 0

    def available(self):
        return self.result

    def poll(self, role):
        return self.polls.pop(0) if len(self.polls) > 1 else self.polls[0]

    def start(self, role, idle_minutes):
        self.started += 1
        return "Started the notebook."

    def stop(self, role):
        self.stopped += 1
        return "The server is shutting down."

    def _load_state(self):
        return {"runs": {"both": {"started": time.time()}}}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.setattr(kaggle, "POLL_SECONDS", 0.01)
    monkeypatch.setattr(kaggle, "WATCH_SECONDS", 0.01)
    monkeypatch.setitem(kaggle._status, "log", [])
    monkeypatch.setitem(kaggle._status, "stage", "off")
    monkeypatch.setitem(kaggle._status, "message", "")
    yield
    kaggle._cancel.set()
    if kaggle._worker:
        kaggle._worker.join(timeout=2)


def run(monkeypatch, launcher):
    monkeypatch.setattr(kaggle, "_load_launcher", lambda: launcher)
    kaggle._cancel.clear()
    kaggle._connect()
    return kaggle.get_status()


def test_starts_a_session_and_reports_each_step(monkeypatch):
    launcher = FakeLauncher(polls=("off", "starting: Kaggle status running, 1 min", "ready", "ready", "off"))
    status = run(monkeypatch, launcher)
    assert launcher.started == 1 and status["username"] == "tester"
    text = " ".join(status["log"])
    for step in ("Checking the Kaggle account", "Signed in as tester", "Sending the notebook", "Kaggle status running", "Connected"):
        assert step in text


def test_joins_a_running_session_without_starting_another(monkeypatch):
    launcher = FakeLauncher(polls=("ready", "off"))
    status = run(monkeypatch, launcher)
    assert launcher.started == 0
    assert any("Connected" in line for line in status["log"])


def test_missing_account_is_reported(monkeypatch):
    launcher = FakeLauncher(available=(False, "no Kaggle credentials"))
    status = run(monkeypatch, launcher)
    assert status["stage"] == "failed" and status["message"] == "no Kaggle credentials" and launcher.started == 0


def test_failed_session_is_reported(monkeypatch):
    status = run(monkeypatch, FakeLauncher(polls=("off", "failed: the notebook ended")))
    assert status["stage"] == "failed" and status["message"] == "the notebook ended"


def test_an_error_does_not_stop_the_backend(monkeypatch):
    launcher = FakeLauncher()
    launcher.start = lambda role, idle_minutes: (_ for _ in ()).throw(RuntimeError("Kaggle refused"))
    status = run(monkeypatch, launcher)
    assert status["stage"] == "failed" and "Kaggle refused" in status["message"]


def test_auto_connect_can_be_turned_off(monkeypatch):
    calls = []
    monkeypatch.setattr(kaggle, "connect", lambda: calls.append(1))
    monkeypatch.setenv("KAGGLE_AUTO_CONNECT", "0")
    kaggle.auto_connect()
    assert calls == []
    monkeypatch.setenv("KAGGLE_AUTO_CONNECT", "1")
    kaggle.auto_connect()
    assert calls == [1]


def test_status_route_and_stop_route(monkeypatch):
    launcher = FakeLauncher()
    monkeypatch.setattr(kaggle, "_load_launcher", lambda: launcher)
    assert client.get("/api/kaggle/status").status_code == 200
    assert client.post("/api/kaggle/stop").json()["stage"] in ("stopping", "off")
    for _ in range(100):
        if launcher.stopped:
            break
        time.sleep(0.01)
    assert launcher.stopped == 1
