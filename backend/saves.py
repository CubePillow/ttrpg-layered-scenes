"""Saved stories. One save is one story, from the party setup through play, so a table can load it from any browser.

A save is a JSON object in layers, so later parts of the game add to it without changing what is already there:

    {
      "version": 2,
      "phase": "setup" | "playing" | "ended",
      "setup": {"title", "count", "party", "style", "gameId"},   # the party, saved on its last step
      "play": null | {
        "act": 2,                                    # the act being played, from 1
        "actState": "writing" | "drawn",             # where that act stands
        "story": [{"heroId", "text"}, ...],          # the shared story text, in pieces by who wrote them
      }
    }

Saves written before this layout (version 1: the setup fields at the top level) are upgraded when they are read,
and the table they were kept in (party_drafts) is moved over once. Pictures do not belong in a save: keep them as
files and put only their id here.

    GET    /api/saves        all saves, newest first, with what the list page shows
    POST   /api/saves        save a new story; returns its id
    GET    /api/saves/{id}   one save, in the current layout
    PUT    /api/saves/{id}   save over it
    DELETE /api/saves/{id}   delete it
"""
import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from games import connect, now

router = APIRouter(prefix="/api/saves", tags=["saves"])

VERSION = 2
PHASES = ("setup", "playing", "ended")
SETUP_KEYS = ("title", "count", "party", "style", "gameId")
ACT_STATES = ("writing", "drawn")
MAX_BYTES = 200_000  # Text only; a long story is still far below this

SCHEMA = """
CREATE TABLE IF NOT EXISTS saves (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
"""


def open_saves(connection):
    """Makes sure the table exists, and moves saves over from the table used before stories were saved in layers."""
    connection.executescript(SCHEMA)
    old = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'party_drafts'").fetchone()
    if old:
        connection.execute("INSERT OR IGNORE INTO saves SELECT id, data, saved_at FROM party_drafts")
        connection.execute("DROP TABLE party_drafts")


def upgrade(data: dict) -> dict:
    """Brings a save from any earlier layout to the current one."""
    if data.get("version") is None:  # Version 1: only the party setup, at the top level
        setup = {key: data[key] for key in SETUP_KEYS if key in data}
        data = {"version": 2, "phase": "setup", "setup": setup, "play": None}
    return data


def check(data) -> dict:
    if not isinstance(data, dict):
        raise HTTPException(400, "a save must be a JSON object")
    data = upgrade(data)
    if data.get("version") != VERSION:
        raise HTTPException(400, f"this backend reads saves of version {VERSION}")
    if data.get("phase") not in PHASES:
        raise HTTPException(400, f"phase must be one of {', '.join(PHASES)}")
    if not isinstance(data.get("setup"), dict):
        raise HTTPException(400, "a save needs its party setup")
    return data


async def read_body(request: Request) -> dict:
    body = await request.body()
    if len(body) > MAX_BYTES:
        raise HTTPException(413, "the save is too large; keep pictures out of it")
    try:
        return check(json.loads(body))
    except ValueError:
        raise HTTPException(400, "the save is not valid JSON")


def progress(data: dict) -> str:
    """A few words for the list page about how far the story got."""
    if data["phase"] == "ended":
        return "Finished"
    if data["phase"] == "playing":
        play = data.get("play") or {}
        if play.get("act") and play.get("actState") in ACT_STATES:
            return f"Act {play['act']} · {play['actState'].capitalize()}"
        if play.get("scene"):  # Saved before acts
            return f"Scene {play['scene']}"
        return "Playing"
    return "Set off"  # A setup is only saved on its last step


def summary(row) -> dict:
    data = upgrade(json.loads(row["data"]))
    setup = data.get("setup") or {}
    party = setup.get("party") if isinstance(setup.get("party"), list) else []
    return {
        "id": row["id"],
        "saved_at": row["saved_at"],
        "title": setup.get("title") or "",
        "phase": data.get("phase"),
        "progress": progress(data),
        "style": setup.get("style"),
        "heroes": [{"name": hero.get("name"), "classId": hero.get("classId"), "color": hero.get("color")}
                   for hero in party if isinstance(hero, dict)],
    }


@router.get("")
def list_saves():
    with connect() as connection:
        open_saves(connection)
        rows = connection.execute("SELECT * FROM saves ORDER BY saved_at DESC").fetchall()
    return [summary(row) for row in rows]


@router.post("", status_code=201)
async def create_save(request: Request):
    data = await read_body(request)
    save_id = uuid4().hex
    with connect() as connection:
        open_saves(connection)
        connection.execute("INSERT INTO saves VALUES (?, ?, ?)", (save_id, json.dumps(data), now()))
    return {"id": save_id}


@router.get("/{save_id}")
def read_save(save_id: str):
    with connect() as connection:
        open_saves(connection)
        row = connection.execute("SELECT data FROM saves WHERE id = ?", (save_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "this save does not exist")
    return upgrade(json.loads(row["data"]))


@router.put("/{save_id}", status_code=204)
async def update_save(save_id: str, request: Request):
    data = await read_body(request)
    with connect() as connection:
        open_saves(connection)
        changed = connection.execute(
            "UPDATE saves SET data = ?, saved_at = ? WHERE id = ?", (json.dumps(data), now(), save_id)
        ).rowcount
    if not changed:
        raise HTTPException(404, "this save does not exist")


@router.delete("/{save_id}", status_code=204)
def delete_save(save_id: str):
    with connect() as connection:
        open_saves(connection)
        connection.execute("DELETE FROM saves WHERE id = ?", (save_id,))
