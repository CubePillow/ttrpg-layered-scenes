import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

HERO = {"id": "h1", "name": "Kragnar", "classId": "barbarian", "color": "#d9534f"}
DRAFT = {"step": 3, "title": "The Ashen Lantern", "count": 2, "party": [HERO], "style": "pixel", "gameId": None}


@pytest.fixture(autouse=True)
def separate_database(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMES_DB", str(tmp_path / "test.db"))


def test_there_are_no_saves_at_first():
    assert client.get("/api/party-drafts").json() == []


def test_a_save_comes_back_as_it_was_stored():
    draft_id = client.post("/api/party-drafts", json=DRAFT).json()["id"]
    assert client.get(f"/api/party-drafts/{draft_id}").json() == DRAFT


def test_the_list_shows_every_save_with_its_title_and_heroes():
    first = client.post("/api/party-drafts", json=DRAFT).json()["id"]
    client.post("/api/party-drafts", json=DRAFT | {"title": "Second"})
    saves = client.get("/api/party-drafts").json()
    assert len(saves) == 2
    mine = next(save for save in saves if save["id"] == first)
    assert mine["title"] == "The Ashen Lantern" and mine["step"] == 3
    assert mine["style"] == "pixel" and mine["players"] == 2
    assert mine["heroes"] == [{"name": "Kragnar", "classId": "barbarian", "color": "#d9534f"}]


def test_saving_again_replaces_only_that_save():
    first = client.post("/api/party-drafts", json=DRAFT).json()["id"]
    second = client.post("/api/party-drafts", json=DRAFT).json()["id"]
    assert client.put(f"/api/party-drafts/{first}", json=DRAFT | {"step": 4}).status_code == 204
    assert client.get(f"/api/party-drafts/{first}").json()["step"] == 4
    assert client.get(f"/api/party-drafts/{second}").json()["step"] == 3


def test_deleting_a_save():
    draft_id = client.post("/api/party-drafts", json=DRAFT).json()["id"]
    assert client.delete(f"/api/party-drafts/{draft_id}").status_code == 204
    assert client.get(f"/api/party-drafts/{draft_id}").status_code == 404
    assert client.put(f"/api/party-drafts/{draft_id}", json=DRAFT).status_code == 404


@pytest.mark.parametrize("body", ["[1, 2]", "{broken", '{"title": "' + "x" * 30_000 + '"}'])
def test_bad_setups_are_refused(body):
    assert client.post("/api/party-drafts", content=body).status_code in (400, 413)
