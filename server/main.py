from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import Config, load_config
from .db.database import init_db
from .routers import events, health, notes, scenes
from .watcher import start_watcher

logger = logging.getLogger(__name__)

_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def create_app(config: Config | None = None) -> FastAPI:
    cfg = config or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.config = cfg
        app.state.db_path = cfg.db_path
        if not cfg.scene_dir.exists():
            logger.error(
                "scene_dir does not exist: %s — check config.toml", cfg.scene_dir
            )
        await init_db(cfg.db_path)
        loop = asyncio.get_running_loop()
        observer = None
        if cfg.scene_dir.exists():
            observer = start_watcher(cfg.scene_dir, loop)
        yield
        if observer is not None:
            observer.stop()
            observer.join()

    app = FastAPI(title="X32 Scene Notes", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(scenes.router)
    app.include_router(notes.router)
    app.include_router(events.router)

    if _FRONTEND_DIR.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(_FRONTEND_DIR), html=True),
            name="frontend",
        )

    return app


app = create_app()


if __name__ == "__main__":
    _cfg = load_config()
    uvicorn.run("server.main:app", host=_cfg.host, port=_cfg.port, reload=False)
