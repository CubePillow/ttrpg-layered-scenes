import base64
import io
from types import SimpleNamespace

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image

import model_api
from main import app

client = TestClient(app)


class NotConnected(RuntimeError):
    pass


def picture(color=(200, 40, 30, 255), size=(32, 32)):
    return Image.new("RGBA", size, color)


def as_text(image=None):
    buffer = io.BytesIO()
    (image or picture()).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def from_text(text):
    prefix, data = text.split(",", 1)
    assert prefix == "data:image/png;base64"
    return Image.open(io.BytesIO(base64.b64decode(data)))


@pytest.fixture
def models(monkeypatch):
    """Stands in for the Kaggle session, so the tests use no GPU quota."""
    calls = {}

    def record(name, result):
        def call(*args, **kwargs):
            calls[name] = (args, kwargs)
            return result
        return call

    class Decomposer:
        def __init__(self, url, token):
            calls["server"] = (url, token)

        def decompose(self, image, params):
            calls["split"] = params
            count = 1 if params.only >= 0 else len(params.names) + 1
            return [picture() for _ in range(count)]

    fake = SimpleNamespace(
        client=SimpleNamespace(
            NotConnected=NotConnected,
            txt2img=record("txt2img", picture()),
            img2img=record("img2img", picture()),
            edit_layer=record("edit", (picture(), {"accepted": True})),
        ),
        connection=SimpleNamespace(load=lambda role: SimpleNamespace(configured=True, url="https://secret.example", token="secret")),
        DecomposeParams=lambda **fields: SimpleNamespace(**fields),
        RemoteDecomposer=Decomposer,
    )
    monkeypatch.setattr(model_api, "_models", lambda: fake)
    fake.calls = calls
    return fake


def test_generate_a_picture(models):
    r = client.post("/api/images/generate", json={"prompt": "  a red fox  ", "seed": 5})
    assert r.status_code == 200
    assert from_text(r.json()["image"]).size == (32, 32)
    assert models.calls["txt2img"][0] == ("a red fox", 5, 4, 512, "")


def test_picture_from_a_sketch(models):
    body = {"prompt": "a tower", "image": "data:image/png;base64," + as_text(), "strength": 0.6}
    r = client.post("/api/images/from-sketch", json=body)
    assert r.status_code == 200
    args = models.calls["img2img"][0]
    assert args[0].size == (32, 32) and args[1:3] == ("a tower", 0.6)


def test_split_returns_named_layers_back_to_front(models):
    r = client.post("/api/images/split", json={"image": as_text(), "names": ["cottage", "red fox"]})
    assert r.status_code == 200
    assert [layer["name"] for layer in r.json()["layers"]] == ["background", "cottage", "red fox"]
    assert models.calls["split"].method == "qwen21-extract"


@pytest.mark.parametrize("only, name", [(0, "background"), (1, "cottage"), (2, "red fox")])
def test_split_one_layer_at_a_time(models, only, name):
    r = client.post("/api/images/split", json={"image": as_text(), "names": ["cottage", "red fox"], "only": only})
    assert [layer["name"] for layer in r.json()["layers"]] == [name]


def test_edit_one_layer(models):
    r = client.post("/api/layers/edit", json={"image": as_text(), "prompt": "make it white"})
    assert r.status_code == 200 and r.json()["report"] == {"accepted": True}
    assert models.calls["edit"][0][1:] == ("make it white", 42)


@pytest.mark.parametrize(
    "path, body",
    [
        ("/api/images/generate", {"prompt": "   "}),
        ("/api/images/generate", {"prompt": "fox", "steps": 99}),
        ("/api/images/generate", {"prompt": "fox", "size": 500}),
        ("/api/images/from-sketch", {"prompt": "fox", "image": as_text(), "strength": 2}),
        ("/api/images/split", {"image": as_text(), "names": []}),
        ("/api/images/split", {"image": as_text(), "names": ["fox"], "only": 2}),
        ("/api/layers/edit", {"image": as_text(), "prompt": ""}),
    ],
)
def test_bad_requests_are_refused(models, path, body):
    assert client.post(path, json=body).status_code == 422
    assert not {"txt2img", "img2img", "split", "edit"} & set(models.calls)


def test_bad_images_are_refused(models):
    assert client.post("/api/layers/edit", json={"image": "not a picture", "prompt": "x"}).status_code == 400
    large = as_text(picture(size=(2049, 8)))
    assert client.post("/api/images/split", json={"image": large, "names": ["fox"]}).status_code == 400


def test_not_connected_gives_a_clear_message(models):
    def refuse(*args):
        raise NotConnected("The server at https://secret.example cannot be reached")

    models.client.txt2img = refuse
    r = client.post("/api/images/generate", json={"prompt": "fox"})
    assert r.status_code == 503 and r.json()["detail"] == model_api.NOT_CONNECTED


def test_split_needs_a_connection(models):
    models.connection.load = lambda role: SimpleNamespace(configured=False)
    assert client.post("/api/images/split", json={"image": as_text(), "names": ["fox"]}).status_code == 503


@pytest.mark.parametrize("error", [requests.ConnectionError("https://secret.example token=secret"), RuntimeError("secret")])
def test_model_errors_do_not_expose_the_kaggle_address(models, error):
    def fail(*args):
        raise error

    models.client.txt2img = fail
    r = client.post("/api/images/generate", json={"prompt": "fox"})
    assert r.status_code == 502 and "secret" not in r.text
