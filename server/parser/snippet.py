from __future__ import annotations

from pathlib import Path

from .parameters import Channel
from .scene import parse_scene


def parse_snippet(path: Path) -> dict[int, Channel]:
    """Parse a .snp snippet file. Returns partial channel data keyed by index."""
    return parse_scene(path)
