from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..db.notes import get_note, list_all_notes
from ..parser import parse_scene
from ..parser.parameters import Channel
from ..parser.writer import merge_scene

router = APIRouter(prefix="/api")


class _PatchItem(BaseModel):
    chn_path: str
    channel_index: int


class _CreateSceneBody(BaseModel):
    source_path: str
    output_name: str
    patches: list[_PatchItem]

_SCENE_EXTS = {".scn", ".snp", ".chn"}
_FILE_TYPES = {".scn": "scene", ".snp": "snippet", ".chn": "channel"}


def _state(request: Request) -> tuple[Path, Path]:
    return request.app.state.config.scene_dir, request.app.state.db_path


def _channel_to_json(ch: Channel) -> dict[str, Any]:
    d = dataclasses.asdict(ch)
    if math.isinf(d.get("fader_db", 0)):
        d["fader_db"] = None
    return d


def _scan(scene_dir: Path) -> list[Path]:
    if not scene_dir.exists():
        return []
    return sorted(
        (f for f in scene_dir.rglob("*") if f.suffix in _SCENE_EXTS),
        key=lambda f: f.name.lower(),
    )


@router.get("/scenes")
async def list_scenes(request: Request) -> dict:
    scene_dir, db_path = _state(request)
    files = _scan(scene_dir)
    notes = await list_all_notes(db_path)

    on_disk = {str(f.relative_to(scene_dir)) for f in files}

    scenes = []
    for f in files:
        rel = str(f.relative_to(scene_dir))
        note_text = notes.get(rel, {}).get("note", "")
        scenes.append(
            {
                "file_path": rel,
                "file_name": f.name,
                "file_type": _FILE_TYPES.get(f.suffix, "unknown"),
                "last_modified": f.stat().st_mtime,
                "has_note": bool(note_text),
                "note_preview": note_text.split("\n")[0][:120] if note_text else "",
            }
        )

    orphaned = [
        {
            "file_path": fp,
            "file_name": v["file_name"],
            "note_preview": v["note"].split("\n")[0][:120],
        }
        for fp, v in notes.items()
        if fp not in on_disk and v.get("note")
    ]

    return {"scenes": scenes, "orphaned_notes": orphaned}


@router.get("/scenes/{file_path:path}")
async def get_scene(file_path: str, request: Request) -> dict:
    scene_dir, db_path = _state(request)
    full_path = scene_dir / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Scene file not found")
    if full_path.suffix not in _SCENE_EXTS:
        raise HTTPException(status_code=400, detail="Not a scene file")

    channels = parse_scene(full_path)
    note = await get_note(db_path, file_path)

    return {
        "file_path": file_path,
        "file_name": full_path.name,
        "file_type": _FILE_TYPES.get(full_path.suffix, "unknown"),
        "last_modified": full_path.stat().st_mtime,
        "note": note.get("note", "") if note else "",
        "channels": {
            str(idx): _channel_to_json(ch)
            for idx, ch in sorted(channels.items())
        },
    }


@router.post("/scenes/create")
async def create_scene(body: _CreateSceneBody, request: Request) -> dict:
    scene_dir, _ = _state(request)

    source_full = scene_dir / body.source_path
    if not source_full.exists() or source_full.suffix not in {".scn", ".snp"}:
        raise HTTPException(400, "Invalid source scene")

    # Strip any directory components from the output name (prevent path traversal)
    output_name = Path(body.output_name).name
    if not output_name:
        raise HTTPException(400, "Invalid output filename")
    if Path(output_name).suffix not in {".scn", ".snp"}:
        output_name += ".scn"

    output_path = source_full.parent / output_name
    if output_path.exists():
        raise HTTPException(409, f"File already exists: {output_name}")

    patch_dict: dict[int, dict[str, list[str]]] = {}
    for item in body.patches:
        chn_full = scene_dir / item.chn_path
        if not chn_full.exists() or chn_full.suffix != ".chn":
            raise HTTPException(400, f"Invalid channel preset: {item.chn_path}")
        channels = parse_scene(chn_full)
        if not channels:
            raise HTTPException(400, f"Could not parse preset: {item.chn_path}")
        ch = next(iter(channels.values()))
        patch_dict[item.channel_index] = ch.raw

    source_text = source_full.read_text(encoding="utf-8", errors="replace")
    merged = merge_scene(source_text, patch_dict)
    output_path.write_text(merged, encoding="utf-8")

    rel = str(output_path.relative_to(scene_dir))
    return {"file_path": rel, "file_name": output_path.name}
