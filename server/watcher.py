from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

_SCENE_EXTENSIONS = {".scn", ".snp", ".chn"}
_subscribers: set[asyncio.Queue] = set()
_loop: asyncio.AbstractEventLoop | None = None


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def _emit(event: dict) -> None:
    if _loop is None:
        return
    for q in list(_subscribers):
        _loop.call_soon_threadsafe(q.put_nowait, event)


class _SceneHandler(FileSystemEventHandler):
    def __init__(self, scene_dir: Path) -> None:
        super().__init__()
        self._scene_dir = scene_dir

    def _rel(self, src_path: str) -> str:
        return str(Path(src_path).relative_to(self._scene_dir))

    def _relevant(self, event: FileSystemEvent) -> bool:
        return (
            not event.is_directory
            and Path(event.src_path).suffix in _SCENE_EXTENSIONS
        )

    def on_created(self, event: FileSystemEvent) -> None:
        if self._relevant(event):
            _emit({"type": "created", "file_path": self._rel(event.src_path)})

    def on_modified(self, event: FileSystemEvent) -> None:
        if self._relevant(event):
            _emit({"type": "modified", "file_path": self._rel(event.src_path)})

    def on_deleted(self, event: FileSystemEvent) -> None:
        if self._relevant(event):
            _emit({"type": "deleted", "file_path": self._rel(event.src_path)})


def start_watcher(scene_dir: Path, loop: asyncio.AbstractEventLoop) -> Observer:
    global _loop
    _loop = loop
    observer = Observer()
    observer.schedule(_SceneHandler(scene_dir), str(scene_dir), recursive=True)
    observer.start()
    logger.info("Watching %s for scene changes", scene_dir)
    return observer
