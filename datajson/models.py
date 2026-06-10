from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DatasetInfo:
    format_name: str
    sample_count: int
    root: Any | None = None
    offsets: tuple[int, ...] = ()
    collection_path: str = "$"
    parse_note: str = ""


@dataclass
class ImageRef:
    raw: str
    exists: bool
    is_url: bool
    resolved: str | None
    status: str


@dataclass
class RenderBlock:
    kind: str
    json_path: str
    schema_name: str
    value: Any
    role: str | None = None
    label: str | None = None
    image: ImageRef | None = None
