"""Pictures drawn during a story. They are kept apart from the save, which holds only their ids.

    POST /api/pictures        {"saveId": "...", "image": "<PNG as base64>"} -> {"id": "..."}
    GET  /api/pictures/{id}   the PNG

A save's pictures are deleted with the save (see saves.delete_save).
"""
import base64
import binascii
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from games import connect, now

router = APIRouter(prefix="/api/pictures", tags=["pictures"])

MAX_BYTES = 8_000_000
PNG_START = b"\x89PNG\r\n\x1a\n"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pictures (
    id TEXT PRIMARY KEY,
    save_id TEXT NOT NULL,
    png BLOB NOT NULL,
    made_at TEXT NOT NULL
);
"""


def open_pictures(connection):
    connection.executescript(SCHEMA)


class NewPicture(BaseModel):
    saveId: str = Field(min_length=1, max_length=64)
    image: str = Field(description="PNG as base64, with or without the 'data:image/png;base64,' prefix")


@router.post("", status_code=201)
def store_picture(picture: NewPicture):
    try:
        png = base64.b64decode(picture.image.split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "the picture is not valid base64")
    if not png.startswith(PNG_START):
        raise HTTPException(400, "the picture must be a PNG")
    if len(png) > MAX_BYTES:
        raise HTTPException(413, "the picture is too large")
    picture_id = uuid4().hex
    with connect() as connection:
        open_pictures(connection)
        connection.execute("INSERT INTO pictures VALUES (?, ?, ?, ?)", (picture_id, picture.saveId, png, now()))
    return {"id": picture_id}


@router.get("/{picture_id}")
def read_picture(picture_id: str):
    with connect() as connection:
        open_pictures(connection)
        row = connection.execute("SELECT png FROM pictures WHERE id = ?", (picture_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "this picture does not exist")
    return Response(row["png"], media_type="image/png", headers={"Cache-Control": "max-age=31536000, immutable"})


def delete_pictures_of(connection, save_id: str):
    open_pictures(connection)
    connection.execute("DELETE FROM pictures WHERE save_id = ?", (save_id,))
