"""Saved games: the title and picture style of each game and the hero, name and colour every player chose.

The data is kept in a SQLite file, backend/data/games.db (set GAMES_DB to use another file).

    POST /api/games        save a new game
    GET  /api/games        all saved games, newest first
    GET  /api/games/{id}   one saved game
    PUT  /api/games/{id}   replace the title, style and players of a saved game
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints, model_validator

DEFAULT_DB = Path(__file__).parent / "data" / "games.db"
MAX_PLAYERS = 6

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    mode TEXT NOT NULL,
    style TEXT NOT NULL DEFAULT 'pixel',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS players (
    game_id TEXT NOT NULL REFERENCES games (id) ON DELETE CASCADE,
    seat INTEGER NOT NULL,
    name TEXT NOT NULL,
    class_id TEXT NOT NULL,
    color TEXT NOT NULL,
    PRIMARY KEY (game_id, seat)
);
"""

ArtStyleId = Literal["pixel", "cartoon", "paper_cutout", "comic"]
HeroClassId = Literal[
    "barbarian", "bard", "cleric", "druid", "fighter", "monk",
    "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
]


class Player(BaseModel):
    seat: int = Field(ge=1, le=MAX_PLAYERS, description="Player number, starting at 1")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=18)]
    class_id: HeroClassId
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class GameIn(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    mode: Literal["local"] = "local"
    style: ArtStyleId = "pixel"
    players: list[Player] = Field(min_length=1, max_length=MAX_PLAYERS)

    @model_validator(mode="after")
    def check_players(self):
        seats = sorted(player.seat for player in self.players)
        if seats != list(range(1, len(seats) + 1)):
            raise ValueError("seats must be numbered 1, 2, 3 ... without gaps")
        colors = [player.color.lower() for player in self.players]
        if len(set(colors)) != len(colors):
            raise ValueError("every player needs a different colour")
        return self


class Game(GameIn):
    id: str
    created_at: str
    updated_at: str


@contextmanager
def connect():
    """One connection per request. Everything inside is saved together, or not at all."""
    path = Path(os.environ.get("GAMES_DB", DEFAULT_DB))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        columns = [column["name"] for column in connection.execute("PRAGMA table_info(games)")]
        if "style" not in columns:  # Games saved before styles existed
            connection.execute("ALTER TABLE games ADD COLUMN style TEXT NOT NULL DEFAULT 'pixel'")
        with connection:
            yield connection
    finally:
        connection.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_players(connection: sqlite3.Connection, game_id: str, players: list[Player]) -> None:
    connection.execute("DELETE FROM players WHERE game_id = ?", (game_id,))
    connection.executemany(
        "INSERT INTO players (game_id, seat, name, class_id, color) VALUES (?, ?, ?, ?, ?)",
        [(game_id, p.seat, p.name, p.class_id, p.color) for p in players],
    )


def read_game(connection: sqlite3.Connection, row: sqlite3.Row) -> Game:
    players = connection.execute(
        "SELECT seat, name, class_id, color FROM players WHERE game_id = ? ORDER BY seat", (row["id"],)
    ).fetchall()
    return Game(**dict(row), players=[Player(**dict(player)) for player in players])


def find_game(connection: sqlite3.Connection, game_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "game not found")
    return row


router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("", response_model=Game, status_code=201)
def create_game(game: GameIn):
    game_id = uuid4().hex
    stamp = now()
    with connect() as connection:
        connection.execute(
            "INSERT INTO games (id, title, mode, style, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (game_id, game.title, game.mode, game.style, stamp, stamp),
        )
        write_players(connection, game_id, game.players)
        return read_game(connection, find_game(connection, game_id))


@router.get("", response_model=list[Game])
def list_games():
    with connect() as connection:
        rows = connection.execute("SELECT * FROM games ORDER BY created_at DESC, rowid DESC").fetchall()
        return [read_game(connection, row) for row in rows]


@router.get("/{game_id}", response_model=Game)
def get_game(game_id: str):
    with connect() as connection:
        return read_game(connection, find_game(connection, game_id))


@router.put("/{game_id}", response_model=Game)
def update_game(game_id: str, game: GameIn):
    with connect() as connection:
        find_game(connection, game_id)
        connection.execute(
            "UPDATE games SET title = ?, mode = ?, style = ?, updated_at = ? WHERE id = ?",
            (game.title, game.mode, game.style, now(), game_id),
        )
        write_players(connection, game_id, game.players)
        return read_game(connection, find_game(connection, game_id))
