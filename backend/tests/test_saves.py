import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

HERO = {"id": "h1", "name": "Kragnar", "classId": "barbarian", "color": "#d9534f"}
SETUP = {"title": "The Ashen Lantern", "count": 1, "party": [HERO], "style": "pixel", "gameId": None}
SAVE = {"version": 2, "phase": "setup", "setup": SETUP, "play": None}


@pytest.fixture(autouse=True)
def separate_database(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMES_DB", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def test_there_are_no_saves_at_first():
    assert client.get("/api/saves").json() == []


def test_a_save_comes_back_as_it_was_stored():
    save_id = client.post("/api/saves", json=SAVE).json()["id"]
    assert client.get(f"/api/saves/{save_id}").json() == SAVE


def test_the_list_shows_title_style_heroes_and_progress():
    save_id = client.post("/api/saves", json=SAVE).json()["id"]
    [listed] = client.get("/api/saves").json()
    assert listed["id"] == save_id and listed["title"] == "The Ashen Lantern" and listed["style"] == "pixel"
    assert listed["phase"] == "setup" and listed["progress"] == "Set off"
    assert listed["heroes"] == [{"name": "Kragnar", "classId": "barbarian", "color": "#d9534f"}]


@pytest.mark.parametrize(
    ("phase", "play", "progress"),
    [
        ("playing", {"scene": 3}, "Scene 3"),
        ("playing", None, "Playing"),
        ("ended", {"scene": 7}, "Finished"),
        ("playing", {"act": 1, "actState": "writing", "story": []}, "Act 1 · Writing"),
        ("playing", {"act": 4, "actState": "drawn"}, "Act 4 · Drawn"),
        ("playing", {"act": 4, "actState": "lost"}, "Playing"),
    ],
)
def test_progress_follows_the_phase(phase, play, progress):
    client.post("/api/saves", json=SAVE | {"phase": phase, "play": play})
    assert client.get("/api/saves").json()[0]["progress"] == progress


def test_saving_again_replaces_only_that_save():
    first = client.post("/api/saves", json=SAVE).json()["id"]
    second = client.post("/api/saves", json=SAVE).json()["id"]
    playing = SAVE | {"phase": "playing", "play": {"scene": 1}}
    assert client.put(f"/api/saves/{first}", json=playing).status_code == 204
    assert client.get(f"/api/saves/{first}").json() == playing
    assert client.get(f"/api/saves/{second}").json() == SAVE


def test_deleting_a_save():
    save_id = client.post("/api/saves", json=SAVE).json()["id"]
    assert client.delete(f"/api/saves/{save_id}").status_code == 204
    assert client.get(f"/api/saves/{save_id}").status_code == 404
    assert client.put(f"/api/saves/{save_id}", json=SAVE).status_code == 404


def test_a_save_in_the_old_layout_is_upgraded():
    save_id = client.post("/api/saves", json=SETUP | {"step": 5}).json()["id"]
    assert client.get(f"/api/saves/{save_id}").json() == SAVE


def test_saves_from_the_old_table_are_moved_over(separate_database):
    connection = sqlite3.connect(separate_database)
    connection.execute("CREATE TABLE party_drafts (id TEXT PRIMARY KEY, data TEXT NOT NULL, saved_at TEXT NOT NULL)")
    connection.execute("INSERT INTO party_drafts VALUES ('old1', ?, '2026-11-20T10:00:00+00:00')", (json.dumps(SETUP | {"step": 5}),))
    connection.commit()
    connection.close()
    assert [save["id"] for save in client.get("/api/saves").json()] == ["old1"]
    assert client.get("/api/saves/old1").json() == SAVE
    tables = sqlite3.connect(separate_database).execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    assert ("party_drafts",) not in tables


@pytest.mark.parametrize(
    "body",
    [
        "[1, 2]",
        "{broken",
        json.dumps(SAVE | {"phase": "lost"}),
        json.dumps(SAVE | {"version": 9}),
        json.dumps({"version": 2, "phase": "setup", "play": None}),
        json.dumps(SAVE | {"play": {"notes": "x" * 210_000}}),
    ],
)
def test_bad_saves_are_refused(body):
    assert client.post("/api/saves", content=body).status_code in (400, 413)
