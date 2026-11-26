import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app

client = TestClient(app)

SAVE = {"version": 2, "phase": "playing", "setup": {"title": "T", "count": 1, "party": [], "style": "pixel", "gameId": None},
        "play": {"scene": 1, "story": [], "scenes": []}}


@pytest.fixture(autouse=True)
def separate_database(tmp_path, monkeypatch):
    monkeypatch.setenv("GAMES_DB", str(tmp_path / "test.db"))


def png_base64():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def test_a_picture_comes_back_as_png():
    picture_id = client.post("/api/pictures", json={"saveId": "s1", "image": png_base64()}).json()["id"]
    response = client.get(f"/api/pictures/{picture_id}")
    assert response.status_code == 200 and response.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(response.content)).size == (4, 4)


@pytest.mark.parametrize("image", ["not base64!", base64.b64encode(b"GIF89a....").decode()])
def test_only_pngs_are_kept(image):
    assert client.post("/api/pictures", json={"saveId": "s1", "image": image}).status_code == 400


def test_deleting_a_save_deletes_its_pictures():
    save_id = client.post("/api/saves", json=SAVE).json()["id"]
    picture_id = client.post("/api/pictures", json={"saveId": save_id, "image": png_base64()}).json()["id"]
    client.delete(f"/api/saves/{save_id}")
    assert client.get(f"/api/pictures/{picture_id}").status_code == 404
