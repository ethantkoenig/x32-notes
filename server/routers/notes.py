from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db.notes import delete_note, get_note, upsert_note

router = APIRouter(prefix="/api")


class NoteBody(BaseModel):
    note: str


def _state(request: Request) -> tuple[Path, Path]:
    return request.app.state.config.scene_dir, request.app.state.db_path


@router.get("/notes/{file_path:path}")
async def get_note_endpoint(file_path: str, request: Request) -> dict:
    _, db_path = _state(request)
    note = await get_note(db_path, file_path)
    if note is None:
        raise HTTPException(status_code=404, detail="No note for this file")
    return note


@router.post("/notes/{file_path:path}")
async def upsert_note_endpoint(
    file_path: str, body: NoteBody, request: Request
) -> dict:
    scene_dir, db_path = _state(request)
    file_name = (scene_dir / file_path).name
    return await upsert_note(db_path, file_path, file_name, body.note)


@router.delete("/notes/{file_path:path}")
async def delete_note_endpoint(file_path: str, request: Request) -> dict:
    _, db_path = _state(request)
    deleted = await delete_note(db_path, file_path)
    if not deleted:
        raise HTTPException(status_code=404, detail="No note for this file")
    return {"deleted": True}
