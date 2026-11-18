import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def separate_database(tmp_path, monkeypatch):
    """Every test gets an empty database, so real saved games are never touched."""
    monkeypatch.setenv("GAMES_DB", str(tmp_path / "test.db"))


def game(**changes):
    return {
        "title": "The Ashen Lantern",
        "mode": "local",
        "players": [
            {"seat": 1, "name": "Kragnar", "class_id": "barbarian", "color": "#d9534f"},
            {"seat": 2, "name": "Aldreon", "class_id": "wizard", "color": "#4f7fd9"},
        ],
    } | changes


def test_save_a_game_and_read_it_back():
    saved = client.post("/api/games", json=game())
    assert saved.status_code == 201
    data = saved.json()
    assert data["id"] and data["created_at"]

    loaded = client.get(f"/api/games/{data['id']}").json()
    assert loaded == data
    assert loaded["title"] == "The Ashen Lantern"
    assert [(p["seat"], p["name"], p["class_id"], p["color"]) for p in loaded["players"]] == [
        (1, "Kragnar", "barbarian", "#d9534f"),
        (2, "Aldreon", "wizard", "#4f7fd9"),
    ]


def test_each_game_is_kept_separately_newest_first():
    first = client.post("/api/games", json=game(title="First")).json()
    second = client.post("/api/games", json=game(title="Second")).json()
    assert [g["id"] for g in client.get("/api/games").json()] == [second["id"], first["id"]]


def test_changing_the_party_replaces_the_old_choices():
    saved = client.post("/api/games", json=game()).json()
    change = game(title="New name", players=[{"seat": 1, "name": "Naoko", "class_id": "monk", "color": "#5fae57"}])
    updated = client.put(f"/api/games/{saved['id']}", json=change)
    assert updated.status_code == 200
    data = client.get(f"/api/games/{saved['id']}").json()
    assert data["title"] == "New name" and data["created_at"] == saved["created_at"]
    assert [p["name"] for p in data["players"]] == ["Naoko"]
    assert len(client.get("/api/games").json()) == 1


def test_names_are_trimmed():
    players = [{"seat": 1, "name": "  Mina  ", "class_id": "bard", "color": "#ff9a3c"}]
    data = client.post("/api/games", json=game(title="  Spaces  ", players=players)).json()
    assert data["title"] == "Spaces" and data["players"][0]["name"] == "Mina"


def test_unknown_game_is_not_found():
    assert client.get("/api/games/missing").status_code == 404
    assert client.put("/api/games/missing", json=game()).status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {"title": "   "},
        {"title": "x" * 41},
        {"mode": "online"},
        {"players": []},
        {"players": [{"seat": 1, "name": "A", "class_id": "dragon", "color": "#d9534f"}]},
        {"players": [{"seat": 1, "name": "A", "class_id": "bard", "color": "red"}]},
        {"players": [{"seat": 2, "name": "A", "class_id": "bard", "color": "#d9534f"}]},
        {"players": [
            {"seat": 1, "name": "A", "class_id": "bard", "color": "#d9534f"},
            {"seat": 2, "name": "B", "class_id": "monk", "color": "#D9534F"},
        ]},
    ],
)
def test_bad_games_are_refused(bad):
    assert client.post("/api/games", json=game(**bad)).status_code == 422
    assert client.get("/api/games").json() == []
