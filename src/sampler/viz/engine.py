from __future__ import annotations

import threading
from collections import deque
from pathlib import Path
from typing import Any

from rich.columns import Columns
from rich.console import Group
from rich.text import Text

from sampler.viz.canvas import render_labeled_graph, render_scanning_seed, render_tree_lines
from sampler.viz.events import (
    STAGE_COLORS,
    STAGE_LABELS,
    DirDiscovered,
    EmbeddingGenerated,
    FileDiscovered,
    FileParsing,
    IndexEvent,
    LogLine,
    PipelineReady,
    ProgressUpdated,
    RelationshipCreated,
    SemanticGraphLoaded,
    Stage,
    StageChanged,
    StatsUpdated,
    SymbolExtracted,
)
from sampler.viz.layout_algo import fruchterman_reingold, radial_layout

MAX_PREVIEW_NODES = 80
MAX_LOG_LINES = 2
EXPANSION_SPEED = 0.008
SEMANTIC_EXPANSION_SPEED = 0.005
LABEL_W = 9


class AnimationEngine:
    """Compact neofetch-style render builder for the Live index experience."""

    def __init__(self, project_name: str) -> None:
        self.project_name = project_name
        self._lock = threading.Lock()
        self.stage = Stage.DISCOVER
        self.frame = 0
        self.progress = 0.0
        self.current_file = ""
        self.stats = {
            "files": 0,
            "symbols": 0,
            "relationships": 0,
            "embeddings": 0,
            "embeddings_total": 0,
            "clusters": 0,
            "queue": 0,
        }
        self.ready_info: dict[str, Any] = {}
        self._dirs: list[str] = []
        self._logs: deque[str] = deque(maxlen=MAX_LOG_LINES)
        self._preview_nodes: list[dict[str, Any]] = []
        self._preview_edges: list[tuple[int, int]] = []
        self._node_id_seq = 1
        self._name_to_node: dict[str, int] = {}
        self._expansion = 0.0
        self._expansion_speed = EXPANSION_SPEED
        self._frozen = False
        self._use_force_layout = False

    def handle(self, event: IndexEvent) -> None:
        with self._lock:
            self._dispatch(event)

    def _dispatch(self, event: IndexEvent) -> None:
        if isinstance(event, StageChanged):
            self.stage = event.stage
            if event.stage == Stage.PARSING:
                self._expansion_speed = EXPANSION_SPEED
            elif event.stage == Stage.RELATIONSHIPS:
                self._expansion_speed = EXPANSION_SPEED * 0.9
            elif event.stage == Stage.EMBEDDINGS:
                self._expansion_speed = EXPANSION_SPEED * 0.7
            if event.stage == Stage.READY:
                self._frozen = True
                self._expansion = 1.0
        elif isinstance(event, DirDiscovered):
            self._dirs.append(event.path)
        elif isinstance(event, FileDiscovered):
            self.stats["files"] = event.index + 1
            self.stats["queue"] = max(0, event.total - event.index - 1)
            self.progress = (event.index / event.total * 30) if event.total else 0
            self._add_log(f"+ {_short_path(event.path)}")
        elif isinstance(event, FileParsing):
            self.current_file = _short_path(event.path)
            base = 30 if event.total else 0
            self.progress = base + (event.index / event.total * 30) if event.total else self.progress
        elif isinstance(event, SymbolExtracted):
            self.stats["symbols"] += 1
            self._ensure_preview_node(event.name)
        elif isinstance(event, RelationshipCreated):
            self.stats["relationships"] += 1
            self._maybe_add_preview_edge(event.source, event.target)
        elif isinstance(event, EmbeddingGenerated):
            self.stats["embeddings"] = event.index
            self.stats["embeddings_total"] = event.total
            base = 60
            self.progress = base + (event.index / event.total * 25) if event.total else self.progress
            if event.total:
                embed_t = event.index / event.total
                self._expansion = max(self._expansion, 0.35 + embed_t * 0.65)
        elif isinstance(event, ProgressUpdated):
            self.progress = event.percent
            if event.message:
                self.current_file = event.message
        elif isinstance(event, StatsUpdated):
            self.stats.update(
                {
                    "files": event.files,
                    "symbols": event.symbols,
                    "relationships": event.relationships,
                    "embeddings": event.embeddings,
                    "embeddings_total": event.embeddings_total,
                    "clusters": event.clusters,
                    "queue": event.queue,
                }
            )
        elif isinstance(event, LogLine):
            self._add_log(event.message)
        elif isinstance(event, SemanticGraphLoaded):
            self._load_semantic_graph(event.nodes, event.edges, event.clusters)
        elif isinstance(event, PipelineReady):
            self.stage = Stage.READY
            self._frozen = True
            self._expansion = 1.0
            self.progress = 100.0
            self.ready_info = {
                "elapsed": event.elapsed_seconds,
                "model": event.embedding_model,
                "nodes": event.nodes,
                "relationships": event.relationships,
                "communities": event.communities,
            }
            self.stats["symbols"] = event.nodes
            self.stats["relationships"] = event.relationships
            if event.nodes:
                self.stats["embeddings_total"] = event.nodes
                self.stats["embeddings"] = max(self.stats["embeddings"], event.nodes)

    def _add_log(self, message: str) -> None:
        self._logs.appendleft(message)

    def _rebuild_targets(self) -> None:
        node_ids = [n["id"] for n in self._preview_nodes]
        if not node_ids:
            return
        if self._use_force_layout:
            fruchterman_reingold(node_ids, self._preview_edges)
        else:
            radial_layout(node_ids)

    def _ensure_preview_node(self, name: str) -> int:
        if name in self._name_to_node:
            return self._name_to_node[name]
        if len(self._preview_nodes) >= MAX_PREVIEW_NODES:
            return self._name_to_node.get(name, 0)
        nid = self._node_id_seq
        self._node_id_seq += 1
        self._name_to_node[name] = nid
        self._preview_nodes.append({"id": nid, "name": name})
        self._rebuild_targets()
        return nid

    def _maybe_add_preview_edge(self, source: str, target: str) -> None:
        src = self._ensure_preview_node(source)
        tgt = self._ensure_preview_node(target)
        if src and tgt and (src, tgt) not in self._preview_edges:
            self._preview_edges.append((src, tgt))

    def _load_semantic_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        clusters: int,
    ) -> None:
        self.stage = Stage.SEMANTIC_GRAPH
        self.stats["clusters"] = clusters
        self._preview_nodes = nodes[:MAX_PREVIEW_NODES]
        self._preview_edges = [(e["source_id"], e["target_id"]) for e in edges]
        self._name_to_node = {n.get("name", str(n["id"])): n["id"] for n in self._preview_nodes}
        self._use_force_layout = True
        self._rebuild_targets()
        self._expansion = max(0.35, self._expansion * 0.6)
        self._expansion_speed = SEMANTIC_EXPANSION_SPEED

    def advance_frame(self) -> None:
        with self._lock:
            if self._frozen:
                return

            self.frame += 1

            if self._expansion < 1.0:
                self._expansion = min(1.0, self._expansion + self._expansion_speed)

            if self.stage == Stage.SEMANTIC_GRAPH and self.progress < 95:
                self.progress = min(95.0, self.progress + 0.15)

    def build_frame(self) -> Group:
        with self._lock:
            return self._build_frame_unlocked()

    def build_layout(self) -> Group:
        """Alias kept for compatibility."""
        return self.build_frame()

    def _build_frame_unlocked(self) -> Group:
        art_col = self._render_art_column()
        info_col = self._render_info_column()
        return Group(Columns([art_col, info_col], padding=(0, 1), expand=False))

    def _kv(self, label: str, value: str, *, value_style: str = "") -> str:
        style = f"[dim]{label:<{LABEL_W}}[/]"
        val = f"[{value_style}]{value}[/]" if value_style else value
        return f"{style} {val}"

    def _mini_bar(self, pct: int, width: int = 10) -> str:
        pct = max(0, min(100, pct))
        filled = int(width * pct / 100)
        return "█" * filled + "░" * (width - filled)

    def _render_info_column(self) -> Text:
        color = STAGE_COLORS[self.stage]
        lines: list[str] = [
            self._kv("project", self.project_name, value_style="bold"),
            self._kv("stage", STAGE_LABELS[self.stage], value_style=f"bold {color}"),
            self._kv("progress", f"{self._mini_bar(int(self.progress))} {int(self.progress)}%"),
            self._kv("files", f"{self.stats['files']:,}"),
            self._kv("symbols", f"{self.stats['symbols']:,}"),
            self._kv("rels", f"{self.stats['relationships']:,}"),
        ]
        emb = self.stats["embeddings"]
        emb_total = self.stats["embeddings_total"]
        if emb_total:
            lines.append(self._kv("embed", f"{emb:,} / {emb_total:,}", value_style="magenta"))
        if self.stats["clusters"]:
            lines.append(self._kv("clusters", str(self.stats["clusters"])))
        if self.current_file and self.stage != Stage.READY:
            lines.append(self._kv("file", self.current_file, value_style="cyan"))
        if self.stage == Stage.READY and self.ready_info:
            model = self.ready_info.get("model", "")
            elapsed = self.ready_info.get("elapsed", 0)
            if model:
                lines.append(self._kv("model", f"{model} · {elapsed:.1f}s", value_style="dim"))
        if self._logs:
            lines.append(self._kv("last", self._logs[0], value_style="dim"))
        return Text.from_markup("\n".join(lines))

    def _render_art_column(self) -> Text:
        color = STAGE_COLORS[self.stage]
        settled = self.stage == Stage.READY

        if self.stage == Stage.DISCOVER:
            lines = render_tree_lines(self._dirs)
        elif self._preview_nodes:
            lines = render_labeled_graph(
                self._preview_nodes,
                self._preview_edges,
                color=color,
                expansion=self._expansion,
                settled=settled,
            )
        else:
            lines = render_scanning_seed(color=color)

        return Text.from_markup("\n".join(lines))


def _short_path(path: str) -> str:
    p = Path(path)
    parts = p.parts
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return p.name