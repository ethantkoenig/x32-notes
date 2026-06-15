from __future__ import annotations

from pathlib import Path

import aiosqlite

_CREATE_NOTES = """
CREATE TABLE IF NOT EXISTS notes (
    file_path   TEXT PRIMARY KEY,
    file_name   TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""


async def init_db(db_path: Path) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_NOTES)
        await db.commit()
