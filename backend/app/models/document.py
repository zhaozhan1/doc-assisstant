from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class FileInfo:
    path: Path
    format: str
    original_archive: Path | None = None


@dataclass
class StructureItem:
    level: int
    text: str
    position: int


@dataclass
class ExtractedDoc:
    text: str
    structure: list[StructureItem]
    metadata: dict = field(default_factory=dict)
    source_path: Path = field(default_factory=Path)


@dataclass
class DocumentMetadata:
    file_name: str
    source_path: str
    import_time: datetime
    doc_date: datetime | None = None
    doc_type: str = ""
    file_md5: str = ""
