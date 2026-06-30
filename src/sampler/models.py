from dataclasses import dataclass
from datetime import datetime


@dataclass
class Project:
    id: int | None
    name: str
    path: str
    language: str
    indexed_at: datetime | None = None


@dataclass
class Symbol:
    id: int | None
    file_id: int
    type: str
    name: str
    qualified_name: str | None = None
    signature: str | None = None
    docstring: str | None = None
    start_line: int = 0
    end_line: int = 0
    metadata: dict | None = None


@dataclass
class Relationship:
    id: int | None
    source_id: int
    target_id: int
    type: str
    line: int | None = None
    metadata: dict | None = None
