"""Real test: calls SDXL-Turbo and Qwen-Image-2.1 in a Kaggle GPU session through the backend API.

This test uses your weekly Kaggle GPU quota, so a normal `python -m pytest` skips it. Run it with:

    python -m pytest -m real -s

It joins a running session, or starts one and waits until it is ready (usually 5 to 12 minutes). A session it had to wait for
is stopped at the end. The pictures are saved to backend/tests/output/real/.
"""
import base64
import io
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageStat

import kaggle_connection as kaggle
from main import app

pytestmark = pytest.mark.real

OUTPUT = Path(__file__).parent / "output" / "real"
CONNECT_TIMEOUT_SECONDS = 30 * 60
PROMPT = "flat colour vector illustration, simple shapes, a red fox on green grass, blue sky"

client = TestClient(app)


def wait_for_stage(stages, timeout):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        status = kaggle.get_status()
        if status["message"] != last:
            last = status["message"]
            print(f"[kaggle] {status['progress']}% {last}", flush=True)
        if status["stage"] in stages:
            return status
        time.sleep(5)
    pytest.fail(f"Kaggle did not reach {stages} within {timeout} seconds. Last message: {last}")


@pytest.fixture(scope="module")
def session():
    launcher = kaggle._load_launcher()
    ok, detail = launcher.available()
    if not ok:
        pytest.fail(f"Kaggle account is not set up: {detail}")
    already_running = launcher.poll(kaggle.ROLE) == "ready" and kaggle._models_ready(launcher)
    if not already_running:
        kaggle.connect()
        status = wait_for_stage({"ready", "failed", "off"}, CONNECT_TIMEOUT_SECONDS)
        if status["stage"] != "ready":
            pytest.fail(f"Could not connect to Kaggle: {status['message']}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    yield
    if not already_running:
        print("[kaggle] Stopping the test session", flush=True)
        client.post("/api/kaggle/stop")
        wait_for_stage({"off", "failed"}, 90)


def decode(text):
    return Image.open(io.BytesIO(base64.b64decode(text.split(",", 1)[1])))


def post(path, body, name=None):
    started = time.time()
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    print(f"[real test] {path}: {time.time() - started:.1f} s", flush=True)
    return response.json()


def assert_is_a_picture(image, size=(512, 512)):
    assert image.size == size
    assert ImageStat.Stat(image.convert("L")).stddev[0] > 5, "the picture is one flat colour"


@pytest.fixture(scope="module")
def scene(session):
    data = post("/api/images/generate", {"prompt": PROMPT, "seed": 7})
    image = decode(data["image"])
    image.save(OUTPUT / "1_generate.png")
    return data["image"]


@pytest.fixture(scope="module")
def fox_layer(scene):
    data = post("/api/images/split", {"image": scene, "names": ["red fox"], "only": 1})
    assert [layer["name"] for layer in data["layers"]] == ["red fox"]
    return data["layers"][0]["image"]


def test_generate_a_picture_from_text(scene):
    assert_is_a_picture(decode(scene))


def test_generate_a_picture_from_a_sketch(session):
    sketch = Image.new("RGB", (512, 512), "white")
    draw = ImageDraw.Draw(sketch)
    draw.rectangle([180, 240, 330, 430], fill=(150, 140, 130), outline="black", width=5)
    draw.polygon([(150, 240), (255, 120), (360, 240)], fill=(170, 60, 50), outline="black")
    buffer = io.BytesIO()
    sketch.save(buffer, format="PNG")
    body = {
        "prompt": "flat colour vector illustration, a small stone house with a red roof",
        "image": base64.b64encode(buffer.getvalue()).decode(),
        "strength": 0.8,
        "seed": 3,
    }
    image = decode(post("/api/images/from-sketch", body)["image"])
    image.save(OUTPUT / "2_from_sketch.png")
    assert_is_a_picture(image)


def test_split_an_object_into_a_transparent_layer(fox_layer):
    image = decode(fox_layer).convert("RGBA")
    image.save(OUTPUT / "3_split_fox.png")
    alpha = image.getchannel("A").histogram()
    visible = sum(alpha[17:]) / sum(alpha)
    assert image.size == (512, 512)
    assert 0.01 < visible < 0.9, f"{visible:.0%} of the layer is visible"


def test_edit_one_layer_with_text(fox_layer):
    data = post("/api/layers/edit", {"image": fox_layer, "prompt": "make the fox white"})
    image = decode(data["image"]).convert("RGBA")
    image.save(OUTPUT / "4_edit_fox.png")
    assert data["report"].get("accepted") is True
    assert_is_a_picture(image)
