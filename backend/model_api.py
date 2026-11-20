"""Image generation and layer editing, run by the models in the Kaggle GPU session.

The frontend calls these routes; the backend keeps the Kaggle address and token to itself.

    POST /api/images/generate      text -> picture (SDXL-Turbo)
    POST /api/images/from-sketch   sketch or picture + text -> picture (SDXL-Turbo)
    POST /api/images/split         picture + object names -> layers (Qwen-Image-2.1)
    POST /api/layers/edit          layer + text -> changed layer (Qwen-Image-2.1)

Images are PNG files as base64 text, with or without the "data:image/png;base64," prefix.
"""
import base64
import binascii
import io
import logging
import threading
import time
from types import SimpleNamespace
from typing import Annotated

import requests
from fastapi import APIRouter, HTTPException
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, StringConstraints, model_validator

from kaggle_connection import _load_launcher

logger = logging.getLogger("uvicorn.error")

MAX_IMAGE_SIDE = 2048
NOT_CONNECTED = "Kaggle is not connected yet. Wait until the connection reaches 100%."
MODEL_FAILED = "The Kaggle session could not finish this request. Please try again."

# The GPU session works on one request at a time
_gpu = threading.Lock()

Prompt = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
ObjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


class GenerateRequest(BaseModel):
    prompt: Prompt
    seed: int = Field(13, ge=0)
    steps: int = Field(4, ge=1, le=8)
    size: int = Field(512, ge=256, le=1024, multiple_of=8)
    negative: str = Field("", max_length=2000)


class SketchRequest(GenerateRequest):
    image: str
    strength: float = Field(0.8, ge=0.05, le=1.0, description="Higher values follow the sketch less")


class SplitRequest(BaseModel):
    image: str
    names: list[ObjectName] = Field(min_length=1, max_length=8, description="The objects to extract, back to front")
    only: int = Field(-1, ge=-1, description="-1: all layers. 0: only the background. 1, 2 ...: only that object")
    seed: int = Field(0, ge=0)

    @model_validator(mode="after")
    def check_only(self):
        if self.only > len(self.names):
            raise ValueError("only must not be larger than the number of names")
        return self


class EditRequest(BaseModel):
    image: str
    prompt: Prompt
    seed: int = Field(42, ge=0)


class ImageResponse(BaseModel):
    image: str


class LayerOut(BaseModel):
    name: str
    image: str


class SplitResponse(BaseModel):
    layers: list[LayerOut]


class EditResponse(ImageResponse):
    report: dict


def _models() -> SimpleNamespace:
    """The prototype's clients for the Kaggle session."""
    _load_launcher()  # Makes the prototype's code available
    from layerproto import connection
    from layerproto.backends import client
    from layerproto.backends.decomposer import DecomposeParams, RemoteDecomposer

    return SimpleNamespace(
        client=client, connection=connection, DecomposeParams=DecomposeParams, RemoteDecomposer=RemoteDecomposer
    )


def decode_image(text: str) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(base64.b64decode(text.split(",", 1)[-1], validate=True)))
        image.load()
    except (binascii.Error, UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "The image is not a valid base64 picture.")
    if max(image.size) > MAX_IMAGE_SIDE:
        raise HTTPException(400, f"The image can be at most {MAX_IMAGE_SIDE} pixels wide and high.")
    return image


def encode_image(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _run(label: str, action):
    """Runs one model request. Error messages never contain the Kaggle address or token."""
    models = _models()
    started = time.time()
    logger.info("[models] %s started", label)
    try:
        with _gpu:
            result = action(models)
    except models.client.NotConnected:
        logger.warning("[models] %s: Kaggle is not connected", label)
        raise HTTPException(503, NOT_CONNECTED)
    except (requests.RequestException, RuntimeError, OSError, ValueError) as error:
        logger.error("[models] %s failed (%s)", label, type(error).__name__)
        raise HTTPException(502, MODEL_FAILED)
    logger.info("[models] %s finished in %.1f s", label, time.time() - started)
    return result


router = APIRouter(prefix="/api", tags=["models"])


@router.post("/images/generate", response_model=ImageResponse)
def generate(request: GenerateRequest):
    picture = _run(
        "Generate",
        lambda m: m.client.txt2img(request.prompt, request.seed, request.steps, request.size, request.negative),
    )
    return ImageResponse(image=encode_image(picture))


@router.post("/images/from-sketch", response_model=ImageResponse)
def from_sketch(request: SketchRequest):
    sketch = decode_image(request.image)
    picture = _run(
        "Sketch to picture",
        lambda m: m.client.img2img(
            sketch, request.prompt, request.strength, request.seed, request.steps, request.size, request.negative
        ),
    )
    return ImageResponse(image=encode_image(picture))


@router.post("/images/split", response_model=SplitResponse)
def split(request: SplitRequest):
    picture = decode_image(request.image)

    def run_split(models):
        server = models.connection.load("split")
        if not server.configured:
            raise models.client.NotConnected(NOT_CONNECTED)
        params = models.DecomposeParams(
            method="qwen21-extract", names=request.names, only=request.only, seed=request.seed, resolution=512
        )
        return models.RemoteDecomposer(server.url, server.token).decompose(picture, params)

    layers = _run("Split", run_split)
    names = ["background", *request.names]
    if request.only >= 0:
        names = [names[request.only]]
    if len(layers) != len(names):
        logger.error("[models] Split returned %d layers instead of %d", len(layers), len(names))
        raise HTTPException(502, MODEL_FAILED)
    return SplitResponse(layers=[LayerOut(name=name, image=encode_image(layer)) for name, layer in zip(names, layers)])


@router.post("/layers/edit", response_model=EditResponse)
def edit_layer(request: EditRequest):
    layer = decode_image(request.image)
    changed, report = _run("Edit layer", lambda m: m.client.edit_layer(layer, request.prompt, request.seed))
    return EditResponse(image=encode_image(changed), report=report)
