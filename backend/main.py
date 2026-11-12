import base64
import binascii
import io

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from pixelize import pixelize, trim, used_colors

app = FastAPI(title="TTRPG Layered Scene Builder API")

# Allow the Vite dev server (frontend) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_SIDE = 2048  # pixels; larger pictures are refused


@app.get("/health")
def health():
    return {"status": "ok"}


class LayerIn(BaseModel):
    name: str
    image: str = Field(description="PNG as base64, with or without the 'data:image/png;base64,' prefix")


class PixelizeRequest(BaseModel):
    layers: list[LayerIn] = Field(min_length=1, max_length=32, description="Back to front; the first one is the background")
    block: int = Field(4, ge=1, le=64, description="Side of one big pixel, in source pixels")
    colors: int = Field(16, ge=2, le=64, description="Size of the shared palette")


class LayerOut(BaseModel):
    name: str
    depth: int
    x: int
    y: int
    width: int
    height: int
    image: str


class PixelizeResponse(BaseModel):
    grid: list[int]
    block: int
    palette: list[str]
    layers: list[LayerOut]


def decode_image(text: str, name: str) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(base64.b64decode(text.split(",", 1)[-1], validate=True)))
        image.load()
    except (binascii.Error, UnidentifiedImageError, OSError):
        raise HTTPException(400, f"layer '{name}' is not a valid base64 image")
    if max(image.size) > MAX_SIDE:
        raise HTTPException(400, f"layer '{name}' is larger than {MAX_SIDE} pixels")
    return image


def encode_image(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


@app.post("/pixelize", response_model=PixelizeResponse)
def pixelize_layers(request: PixelizeRequest):
    """Give all layers the same big-pixel grid and the same palette. Each layer comes back on its own, cut to its content."""
    images = [decode_image(layer.image, layer.name) for layer in request.layers]
    small = pixelize(images, request.block, request.colors)
    layers = []
    for depth, (layer, image) in enumerate(zip(request.layers, small)):
        cut, (x, y) = trim(image)
        layers.append(LayerOut(name=layer.name, depth=depth, x=x, y=y, width=cut.width, height=cut.height, image=encode_image(cut)))
    return PixelizeResponse(grid=list(small[0].size), block=request.block, palette=used_colors(small), layers=layers)
