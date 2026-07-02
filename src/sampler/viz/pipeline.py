from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.indexer.embedder import Embedder
from sampler.viz.bus import EventBus, NullEventBus
from sampler.viz.engine import AnimationEngine
from sampler.viz.events import PipelineReady, SemanticGraphLoaded, Stage, StageChanged, StatsUpdated
from sampler.viz.live import IndexLiveSession

if TYPE_CHECKING:
    from rich.console import Console

    from sampler.config import ProjectConfig


def load_semantic_preview(db: Database, project_name: str, bus: EventBus | NullEventBus) -> int:
    bus.emit(StageChanged(Stage.SEMANTIC_GRAPH))
    rows = db.get_top_symbols_by_degree(project_name, limit=80)
    if not rows:
        bus.emit(SemanticGraphLoaded(nodes=[], edges=[], clusters=0))
        return 0

    nodes = [
        {
            "id": int(r["id"]),
            "name": r["qualified_name"] or r["name"],
            "type": r["type"],
        }
        for r in rows
    ]
    node_ids = [n["id"] for n in nodes]
    edge_rows = db.get_relationships_among(node_ids)
    edges = [
        {"source_id": int(e["source_id"]), "target_id": int(e["target_id"]), "type": e["type"]}
        for e in edge_rows
    ]
    clusters = estimate_clusters(node_ids, edges)
    bus.emit(SemanticGraphLoaded(nodes=nodes, edges=edges, clusters=clusters))
    return clusters


def estimate_clusters(node_ids: list[int], edges: list[dict[str, Any]]) -> int:
    if not node_ids:
        return 0
    parent = {nid: nid for nid in node_ids}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    id_set = set(node_ids)
    for e in edges:
        s, t = e["source_id"], e["target_id"]
        if s in id_set and t in id_set:
            union(s, t)
    return max(1, len({find(n) for n in node_ids}))


def _run_pipeline_body(
    db: Database,
    project_cfg: ProjectConfig,
    embedder: Embedder,
    bus: EventBus | NullEventBus,
    *,
    force: bool,
    batch_size: int,
    started: float,
) -> dict[str, Any]:
    builder = IndexBuilder(db=db)
    index_stats = builder.index_project(
        project_name=project_cfg.name,
        project_path=project_cfg.path,
        language=project_cfg.language,
        force=force,
        event_bus=bus,
    )
    communities = load_semantic_preview(db, project_cfg.name, bus)
    bus.emit(StageChanged(Stage.EMBEDDINGS))
    embed_count = embedder.embed_project(
        db=db,
        project_name=project_cfg.name,
        batch_size=batch_size,
        event_bus=bus,
    )
    stats = db.get_project_index_stats(project_cfg.name)
    elapsed = time.monotonic() - started
    model = getattr(embedder.provider, "model_id", embedder.backend)
    bus.emit(
        StatsUpdated(
            files=stats["files"],
            symbols=stats["symbols"],
            relationships=stats["relationships"],
            embeddings=stats["embeddings"],
            embeddings_total=stats["symbols"],
            clusters=communities or 0,
        )
    )
    bus.emit(
        PipelineReady(
            elapsed_seconds=elapsed,
            embedding_model=model,
            nodes=stats["symbols"],
            relationships=stats["relationships"],
            communities=communities or 1,
        )
    )
    return {
        **index_stats,
        "embed_count": embed_count,
        "elapsed": elapsed,
        "model": model,
        "symbols": stats["symbols"],
        "relationships": stats["relationships"],
    }


def run_index_pipeline(
    db: Database,
    project_cfg: ProjectConfig,
    embedder: Embedder,
    *,
    force: bool = False,
    batch_size: int = 32,
    plain: bool = False,
    console: Console | None = None,
) -> dict[str, Any]:
    """Run full index + embed pipeline with optional Live visualization."""
    started = time.monotonic()
    if plain:
        return _run_pipeline_body(
            db,
            project_cfg,
            embedder,
            NullEventBus(),
            force=force,
            batch_size=batch_size,
            started=started,
        )

    bus = EventBus()
    engine = AnimationEngine(project_name=project_cfg.name)
    with IndexLiveSession(engine, bus, console=console):
        return _run_pipeline_body(
            db,
            project_cfg,
            embedder,
            bus,
            force=force,
            batch_size=batch_size,
            started=started,
        )