from rich.console import Console

from sampler.cli.render import render_bars


def test_render_bars_groups_connected_symbols_by_color(capsys) -> None:
    rows = [
        {"id": 1, "qualified_name": "Calculator", "start_line": 1},
        {"id": 2, "qualified_name": "Calculator.total", "start_line": 2},
        {"id": 3, "qualified_name": "unrelated_helper", "start_line": 10},
    ]
    edges = [{"source_id": 1, "target_id": 2, "type": "CONTAINS", "line": 2}]

    console = Console(record=True, force_terminal=True, color_system="standard")
    render_bars(console, rows, edges, lambda r: r["qualified_name"])
    output = console.export_text()

    assert "Calculator" in output
    assert "Calculator.total" in output
    assert "unrelated_helper" in output
    # The related pair should be annotated with an arrow to the other symbol.
    assert "CONTAINS" in output


def test_render_bars_falls_back_to_plain_when_no_ids() -> None:
    rows = [{"qualified_name": "foo"}, {"qualified_name": "bar"}]
    console = Console(record=True)
    render_bars(console, rows, [], lambda r: r["qualified_name"])
    output = console.export_text()
    assert "foo" in output
    assert "bar" in output
