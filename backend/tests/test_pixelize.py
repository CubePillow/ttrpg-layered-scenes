import base64
import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from pixelize import pixelize

client = TestClient(app)


def scene():
    """A blue-to-dark background and a red square with a soft edge, both 64 x 64."""
    gradient = np.zeros((64, 64, 4), np.uint8)
    gradient[..., 2] = np.linspace(60, 200, 64, dtype=np.uint8)[:, None]
    gradient[..., 3] = 255
    square = np.zeros((64, 64, 4), np.uint8)
    square[16:40, 24:48] = (220, 40, 30, 255)
    square[16:40, 22:24] = (220, 40, 30, 90)  # soft edge, must disappear
    return [Image.fromarray(gradient), Image.fromarray(square)]


def as_base64(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def from_base64(text):
    return Image.open(io.BytesIO(base64.b64decode(text.split(",", 1)[1]))).convert("RGBA")


def test_layers_share_grid_and_palette():
    small = pixelize(scene(), block=4, colors=6)
    assert [l.size for l in small] == [(16, 16), (16, 16)]
    colors = set()
    for layer in small:
        a = np.asarray(layer)
        colors |= {tuple(c) for c in a[a[..., 3] > 0][:, :3]}
    assert len(colors) <= 6


def test_alpha_is_on_or_off_and_object_keeps_its_place():
    square = np.asarray(pixelize(scene(), block=4, colors=6)[1])
    assert set(np.unique(square[..., 3])) <= {0, 255}
    ys, xs = np.nonzero(square[..., 3])
    assert (xs.min(), xs.max() + 1, ys.min(), ys.max() + 1) == (6, 12, 4, 10)
    r, g, b = square[5, 8, :3]
    assert r > 150 and g < 90 and b < 90  # the small red object keeps its colour next to a large blue background


def test_endpoint_returns_each_layer_cut_to_its_content():
    background, square = scene()
    body = {"layers": [{"name": "background", "image": as_base64(background)},
                       {"name": "square", "image": "data:image/png;base64," + as_base64(square)}],
            "block": 4, "colors": 6}
    r = client.post("/pixelize", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["grid"] == [16, 16] and data["block"] == 4 and 1 <= len(data["palette"]) <= 6
    bg, sq = data["layers"]
    assert (bg["name"], bg["depth"], bg["x"], bg["y"], bg["width"], bg["height"]) == ("background", 0, 0, 0, 16, 16)
    assert (sq["name"], sq["depth"], sq["x"], sq["y"], sq["width"], sq["height"]) == ("square", 1, 6, 4, 6, 6)
    assert from_base64(sq["image"]).size == (6, 6)


def test_endpoint_refuses_bad_input():
    assert client.post("/pixelize", json={"layers": [{"name": "x", "image": "not an image"}]}).status_code == 400
    assert client.post("/pixelize", json={"layers": []}).status_code == 422
    ok = as_base64(scene()[0])
    assert client.post("/pixelize", json={"layers": [{"name": "x", "image": ok}], "block": 0}).status_code == 422
