from __future__ import annotations

from typing import Callable

from rich.console import Console

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
