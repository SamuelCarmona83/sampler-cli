from __future__ import annotations

from typing import Callable

from rich.console import Console
from rich.table import Table

# Rotating color palette used to give each connected group of symbols its own
# color, similar to how rhyme schemes are color-coded in rap/hip-hop lyric
# breakdowns (this project draws inspiration from MF DOOM's dense internal
# rhyme patterns).
_PALETTE = [
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
]

_ARROWS = {"CALLS": "→", "CONTAINS": "⊃", "IMPORTS": "⇒"}
_BAR = "\u258e"  # ▎


def _type_color(typ: str | None) -> str:
    t = (typ or "").lower()
    if "function" in t or "method" in t:
        return "green"
    if "class" in t or "interface" in t:
        return "blue"
    return "cyan"


def format_symbol_line(r: dict, roots: dict | None = None, show_project: bool = True) -> str:
    """Return a rich-markup formatted compact line for a symbol row.

    Used by CLI for consistent clean output across search/symbols/callers etc.
    """
    from sampler.cli.main import _short_path, _format_line_range  # avoid circular at import time

    if roots is None:
        roots = {}
    shortf = _short_path(r.get("project_name", ""), r.get("file_path", ""), roots)
    name = r.get("qualified_name") or r.get("name") or ""
    lines = _format_line_range(r.get("start_line"), r.get("end_line"))
    typ = r.get("type")
    col = _type_color(typ)
    proj = f"[dim]{r.get('project_name', '')}[/]: " if show_project else ""
    return (
        f"{proj}[dim]{shortf}:{lines}[/] "
        f"[{col}]{typ or 'symbol'}[/] [bold]{name}[/bold]"
    )


def render_symbols_table(console: Console, rows: list[dict], title: str = "Symbols") -> None:
    """Clean table renderer for symbols/search results (used when --style table or for lists)."""
    if not rows:
        console.print("[dim]No results.[/dim]")
        return
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Location", style="dim")
    table.add_column("Type", style="green")
    table.add_column("Name", style="bold")
    table.add_column("Signature", style="dim")

    for r in rows:
        short = r.get("file_path", "")
        if "project_name" in r:
            # try to shorten if possible (caller may pass roots)
            pass
        lines = f"{r.get('start_line', '-')}"
        if r.get("end_line") and r.get("end_line") != r.get("start_line"):
            lines += f"-{r['end_line']}"
        loc = f"{r.get('project_name', '')}:{short}:{lines}"
        typ = r.get("type", "")
        name = r.get("qualified_name") or r.get("name", "")
        sig = r.get("signature") or ""
        col = _type_color(typ)
        table.add_row(loc, f"[{col}]{typ}[/{col}]", name, sig)
    console.print(table)


class _UnionFind:
    def __init__(self, items: list[int]) -> None:
        self.parent = {i: i for i in items}

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def render_bars(
    console: Console,
    rows: list[dict],
    edges: list[dict],
    format_line: Callable[[dict], str],
) -> None:
    """Render rows with colored bars connecting related symbols (rhyme-scheme style),
    plus ascii arrows annotating each relation to other rows in the same result set.

    - rows: symbol dicts, each should include an "id" key when available.
    - edges: relationship dicts with source_id/target_id/type, restricted to rows in view.
    - format_line: renders a row into its normal (non-bars) display line.
    """
    ids = [r["id"] for r in rows if r.get("id") is not None]
    if not ids:
        for row in rows:
            console.print(format_line(row))
        return

    uf = _UnionFind(ids)
    id_set = set(ids)
    relevant_edges = [e for e in edges if e["source_id"] in id_set and e["target_id"] in id_set]
    for edge in relevant_edges:
        uf.union(edge["source_id"], edge["target_id"])

    groups: dict[int, list[int]] = {}
    for symbol_id in ids:
        groups.setdefault(uf.find(symbol_id), []).append(symbol_id)

    color_by_root: dict[int, str] = {}
    color_idx = 0
    for root, members in groups.items():
        if len(members) < 2:
            continue
        color_by_root[root] = _PALETTE[color_idx % len(_PALETTE)]
        color_idx += 1

    id_to_row = {r["id"]: r for r in rows if r.get("id") is not None}
    outgoing: dict[int, list[dict]] = {}
    for edge in relevant_edges:
        outgoing.setdefault(edge["source_id"], []).append(edge)

    for row in rows:
        rid = row.get("id")
        line = format_line(row)
        if rid is None:
            console.print(f"  {line}")
            continue

        color = color_by_root.get(uf.find(rid))
        bar = f"[{color}]{_BAR}[/{color}] " if color else "  "

        annotations = []
        for edge in outgoing.get(rid, []):
            target_row = id_to_row.get(edge["target_id"])
            if not target_row:
                continue
            arrow = _ARROWS.get(edge["type"], "→")
            target_name = target_row.get("qualified_name") or target_row.get("name")
            annotations.append(f"{arrow} {edge['type']} {target_name}:{target_row.get('start_line', '-')}")
        suffix = "  " + "  ".join(annotations) if annotations else ""

        if color:
            console.print(f"{bar}[{color}]{line}[/{color}]{suffix}")
        else:
            console.print(f"{bar}{line}{suffix}")
