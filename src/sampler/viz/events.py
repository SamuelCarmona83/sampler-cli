from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Stage(str, Enum):
    DISCOVER = "discover"
    PARSING = "parsing"
    RELATIONSHIPS = "relationships"
    EMBEDDINGS = "embeddings"
    SEMANTIC_GRAPH = "semantic_graph"
    READY = "ready"


STAGE_LABELS: dict[Stage, str] = {
    Stage.DISCOVER: "Discovering files",
    Stage.PARSING: "Parsing symbols",
    Stage.RELATIONSHIPS: "Building relationships",
    Stage.EMBEDDINGS: "Generating embeddings",
    Stage.SEMANTIC_GRAPH: "Organizing knowledge graph",
    Stage.READY: "ready",
}

STAGE_COLORS: dict[Stage, str] = {
    Stage.DISCOVER: "blue",
    Stage.PARSING: "yellow",
    Stage.RELATIONSHIPS: "green",
    Stage.EMBEDDINGS: "magenta",
    Stage.SEMANTIC_GRAPH: "cyan",
    Stage.READY: "cyan",
}


@dataclass(frozen=True)
class StageChanged:
    stage: Stage


@dataclass(frozen=True)
class DirDiscovered:
    path: str


@dataclass(frozen=True)
class FileDiscovered:
    path: str
    index: int = 0
    total: int = 0


@dataclass(frozen=True)
class FileParsing:
    path: str
    index: int = 0
    total: int = 0


@dataclass(frozen=True)
class SymbolExtracted:
    name: str
    symbol_type: str = "symbol"
    file_path: str = ""


@dataclass(frozen=True)
class RelationshipCreated:
    source: str
    target: str
    relation_type: str = "CALLS"


@dataclass(frozen=True)
class EmbeddingGenerated:
    name: str
    index: int = 0
    total: int = 0


@dataclass(frozen=True)
class ProgressUpdated:
    percent: float
    message: str = ""


@dataclass(frozen=True)
class StatsUpdated:
    files: int = 0
    symbols: int = 0
    relationships: int = 0
    embeddings: int = 0
    embeddings_total: int = 0
    clusters: int = 0
    queue: int = 0


@dataclass(frozen=True)
class LogLine:
    message: str


@dataclass(frozen=True)
class SemanticGraphLoaded:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    clusters: int = 0


@dataclass(frozen=True)
class PipelineReady:
    elapsed_seconds: float = 0.0
    embedding_model: str = ""
    nodes: int = 0
    relationships: int = 0
    communities: int = 0


IndexEvent = (
    StageChanged
    | DirDiscovered
    | FileDiscovered
    | FileParsing
    | SymbolExtracted
    | RelationshipCreated
    | EmbeddingGenerated
    | ProgressUpdated
    | StatsUpdated
    | LogLine
    | SemanticGraphLoaded
    | PipelineReady
)