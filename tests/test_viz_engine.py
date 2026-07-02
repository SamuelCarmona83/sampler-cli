from sampler.viz.engine import AnimationEngine
from sampler.viz.events import (
    FileDiscovered,
    PipelineReady,
    RelationshipCreated,
    Stage,
    StageChanged,
    SymbolExtracted,
)


def test_engine_advances_through_discover_and_symbols() -> None:
    engine = AnimationEngine(project_name="demo")
    engine.handle(StageChanged(Stage.DISCOVER))
    engine.handle(FileDiscovered(path="/proj/a.py", index=0, total=2))
    engine.handle(StageChanged(Stage.PARSING))
    engine.handle(SymbolExtracted(name="main", symbol_type="function"))
    engine.handle(RelationshipCreated(source="main", target="helper", relation_type="CALLS"))
    engine.advance_frame()

    assert engine.stats["files"] == 1
    assert engine.stats["symbols"] == 1
    assert engine.stats["relationships"] == 1
    frame = engine.build_frame()
    assert frame is not None


def test_pipeline_ready_syncs_stats_from_db() -> None:
    engine = AnimationEngine(project_name="demo")
    engine.handle(
        PipelineReady(
            elapsed_seconds=1.0,
            embedding_model="hash",
            nodes=142,
            relationships=50,
            communities=9,
        )
    )
    assert engine.stats["symbols"] == 142
    assert engine.stats["relationships"] == 50


def test_engine_ready_freezes_without_pulse() -> None:
    engine = AnimationEngine(project_name="demo")
    engine.handle(StageChanged(Stage.PARSING))
    engine.handle(SymbolExtracted(name="main", symbol_type="function"))
    engine.handle(
        PipelineReady(
            elapsed_seconds=1.5,
            embedding_model="hash",
            nodes=10,
            relationships=5,
            communities=2,
        )
    )
    frame_before = engine.frame
    expansion_before = engine._expansion
    engine.advance_frame()
    assert engine.stage == Stage.READY
    assert engine.frame == frame_before
    assert engine._expansion == expansion_before == 1.0
    assert engine.build_frame() is not None


def test_engine_expands_graph_over_time() -> None:
    engine = AnimationEngine(project_name="demo")
    engine.handle(StageChanged(Stage.PARSING))
    engine.handle(SymbolExtracted(name="a", symbol_type="function"))
    engine.handle(SymbolExtracted(name="b", symbol_type="function"))
    engine.handle(RelationshipCreated(source="a", target="b", relation_type="CALLS"))
    before = engine._expansion
    for _ in range(30):
        engine.advance_frame()
    assert engine._expansion > before