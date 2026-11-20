"""Party setups saved with the Save button, so a table can pick one and continue it from any browser.

They are kept in the same SQLite file as the saved games.

    GET    /api/party-drafts        all saves, newest first (title, step, style, players, heroes, time)
    POST   /api/party-drafts        save a new setup; returns its id
    GET    /api/party-drafts/{id}   one save, as it was stored
    PUT    /api/party-drafts/{id}   save over it
    DELETE /api/party-drafts/{id}   delete it
"""
import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from games import connect, now

router = APIRouter(prefix="/api/party-drafts", tags=["party drafts"])

MAX_BYTES = 20_000  # A full party of six heroes is about 1 KB

SCHEMA = """
CREATE TABLE IF NOT EXISTS party_drafts (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
"""


async def read_body(request: Request) -> dict:
    body = await request.body()
    if len(body) > MAX_BYTES:
        raise HTTPException(413, "the party setup is too large")
    try:
        draft = json.loads(body)
    except ValueError:
        raise HTTPException(400, "the party setup is not valid JSON")
    if not isinstance(draft, dict):
        raise HTTPException(400, "the party setup must be a JSON object")
    return draft


def summary(row) -> dict:
    data = json.loads(row["data"])
    party = data.get("party") if isinstance(data.get("party"), list) else []
    return {
        "id": row["id"],
        "saved_at": row["saved_at"],
        "title": data.get("title") or "",
        "step": data.get("step", 0),
        "style": data.get("style"),
        "players": data.get("count", len(party)),
        "heroes": [{"name": hero.get("name"), "classId": hero.get("classId"), "color": hero.get("color")}
                   for hero in party if isinstance(hero, dict)],
    }


@router.get("")
def list_drafts():
    with connect() as connection:
        connection.executescript(SCHEMA)
        rows = connection.execute("SELECT * FROM party_drafts ORDER BY saved_at DESC").fetchall()
    return [summary(row) for row in rows]


@router.post("", status_code=201)
async def create_draft(request: Request):
    draft = await read_body(request)
    draft_id = uuid4().hex
    with connect() as connection:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO party_drafts VALUES (?, ?, ?)", (draft_id, json.dumps(draft), now()))
    return {"id": draft_id}


@router.get("/{draft_id}")
def read_draft(draft_id: str):
    with connect() as connection:
        connection.executescript(SCHEMA)
        row = connection.execute("SELECT data FROM party_drafts WHERE id = ?", (draft_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "this save does not exist")
    return json.loads(row["data"])


@router.put("/{draft_id}", status_code=204)
async def update_draft(draft_id: str, request: Request):
    draft = await read_body(request)
    with connect() as connection:
        connection.executescript(SCHEMA)
        changed = connection.execute(
            "UPDATE party_drafts SET data = ?, saved_at = ? WHERE id = ?", (json.dumps(draft), now(), draft_id)
        ).rowcount
    if not changed:
        raise HTTPException(404, "this save does not exist")


@router.delete("/{draft_id}", status_code=204)
def delete_draft(draft_id: str):
    with connect() as connection:
        connection.executescript(SCHEMA)
        connection.execute("DELETE FROM party_drafts WHERE id = ?", (draft_id,))
