from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source_file: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
