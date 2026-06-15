from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    host: str = "0.0.0.0"
    port: int = 8765
    scene_dir: Path = field(
        default_factory=lambda: Path.home() / "Documents" / "X32Edit" / "Scenes"
    )
    db_path: Path = field(default_factory=lambda: Path("notes.db"))


def load_config(path: Path = Path("config.toml")) -> Config:
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    server = data.get("server", {})
    x32 = data.get("x32", {})
    return Config(
        host=server.get("host", "0.0.0.0"),
        port=int(server.get("port", 8765)),
        scene_dir=Path(
            x32.get("scene_dir", Path.home() / "Documents" / "X32Edit" / "Scenes")
        ),
    )
