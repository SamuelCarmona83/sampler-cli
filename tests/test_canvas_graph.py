import re

from sampler.viz.canvas import (
    ART_ROWS,
    _short_label,
    render_labeled_graph,
    render_scanning_seed,
    render_tree_lines,
)


def _plain(markup: str) -> str:
    return re.sub(r"\[/?[^\]]+\]", "", markup)


def test_short_label_prefers_symbol_tail() -> None:
    assert _short_label("sync_all_mpymporter::init") == "init"
    assert _short_label("test_elastic.TestPerformance.test_create_index") == "create"
    assert _short_label("sync_all_mpymporter::prefetch_m") == "prefetch"


def test_render_labeled_graph_shows_names_and_edges() -> None:
    nodes = [
        {"id": 1, "name": "module.main"},
        {"id": 2, "name": "module.util"},
        {"id": 3, "name": "module.core"},
    ]
    lines = render_labeled_graph(nodes, [(1, 2), (2, 3), (1, 3)], expansion=1.0, settled=True)
    text = _plain("\n".join(lines))
    assert "main" in text
    assert "util" in text
    assert "─" in text
    assert "│" in text
    assert len(lines) == ART_ROWS


def test_all_hubs_get_connected_edges() -> None:
    nodes = [
        {"id": 1, "name": "truncate"},
        {"id": 2, "name": "run"},
        {"id": 3, "name": "parse"},
        {"id": 4, "name": "summoner"},
        {"id": 5, "name": "backfill"},
        {"id": 6, "name": "summoner2"},
    ]
    # Only connect bottom cluster; top hubs have no direct edge between them.
    edges = [(4, 5), (5, 6), (4, 6)]
    text = _plain("\n".join(render_labeled_graph(nodes, edges, expansion=1.0)))
    assert "truncate" in text
    assert "run" in text
    # Spokes should connect isolated top hubs into the graph.
    assert text.count("│") + text.count("─") >= 6


def test_edges_grow_with_expansion() -> None:
    nodes = [
        {"id": 1, "name": "alpha"},
        {"id": 2, "name": "beta"},
    ]
    low = _plain("\n".join(render_labeled_graph(nodes, [(1, 2)], expansion=0.3)))
    high = _plain("\n".join(render_labeled_graph(nodes, [(1, 2)], expansion=1.0)))
    assert high.count("│") + high.count("─") >= low.count("│") + low.count("─")


def test_render_tree_lines_padded_to_art_rows() -> None:
    lines = render_tree_lines([])
    assert len(lines) == ART_ROWS
    assert "scanning" in lines[1]


def test_render_scanning_seed_padded() -> None:
    lines = render_scanning_seed()
    assert len(lines) == ART_ROWS
    assert "scanning" in lines[0]