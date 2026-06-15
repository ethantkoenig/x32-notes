from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_note(db_path: Path, file_path: str) -> Optional[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM notes WHERE file_path = ?", (file_path,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def upsert_note(
    db_path: Path, file_path: str, file_name: str, note: str
) -> dict:
    now = _now()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO notes (file_path, file_name, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                note       = excluded.note,
                updated_at = excluded.updated_at
            """,
            (file_path, file_name, note, now, now),
        )
        await db.commit()
    return await get_note(db_path, file_path)


async def delete_note(db_path: Path, file_path: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "DELETE FROM notes WHERE file_path = ?", (file_path,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def list_all_notes(db_path: Path) -> dict[str, dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM notes") as cursor:
            rows = await cursor.fetchall()
            return {row["file_path"]: dict(row) for row in rows}
