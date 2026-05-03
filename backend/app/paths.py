from __future__ import annotations

import sys
from pathlib import Path

_APP_NAME = "doc-assistant"


def get_data_dir() -> Path:
    base = Path.home() / "Library" / "Application Support" if getattr(sys, "frozen", False) else Path.cwd()
    data_dir = base / _APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def resolve_path(path_str: str) -> str:
    p = Path(path_str)
    if p.is_absolute():
        return path_str
    return str(get_data_dir() / p)
