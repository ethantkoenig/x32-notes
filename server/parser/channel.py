from __future__ import annotations

from pathlib import Path
from typing import Optional

from .parameters import Channel
from .scene import parse_scene


def parse_channel(path: Path) -> Optional[Channel]:
    """Parse a .chn preset file. Returns the channel, or None if the file is empty."""
    channels = parse_scene(path)
    if not channels:
        return None
    return channels[min(channels)]
