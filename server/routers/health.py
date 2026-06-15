from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()

_SCENE_EXTS = {".scn", ".snp", ".chn"}


@router.get("/health")
async def health(request: Request) -> dict:
    scene_dir = request.app.state.config.scene_dir
    scene_count = (
        sum(1 for f in scene_dir.rglob("*") if f.suffix in _SCENE_EXTS)
        if scene_dir.exists()
        else 0
    )
    return {
        "status": "ok",
        "scene_count": scene_count,
        "scene_dir": str(scene_dir),
        "scene_dir_exists": scene_dir.exists(),
    }
