from __future__ import annotations

from typing import Any, Sequence

from sampler.viz.layout_algo import ease_out_cubic

ART_COLS = 34
ART_ROWS = 16
MAX_HUBS = 6
MAX_HUB_EDGES = 8
LABEL_MAX = 8
_EDGE_CHARS = frozenset("─│┌┐└┘╲╱·")

# Target slots inside the frame (col, row).
HUB_SLOTS: list[tuple[int, int]] = [
    (17, 3),
    (7, 7),
    (27, 7),
    (7, 11),
    (27, 11),
    (17, 13),
]
_CENTER = (ART_COLS // 2, ART_ROWS // 2)


def render_tree_lines(dirs: Sequence[str], *, max_lines: int = 14) -> list[str]:
    """Render a compact directory tree for the discover stage."""
    if not dirs:
        lines = ["📁 project", "  (scanning...)"]
    else:
        unique = sorted(set(dirs))[:max_lines]
        lines = ["📁 project"]
        for d in unique:
            depth = d.count("/") + d.count("\\")
            indent = "  " * min(depth + 1, 3)
            name = d.split("/")[-1].split("\\")[-1] or d
            prefix = "└── " if depth else "├── "
            lines.append(f"{indent}{prefix}{name}")
        if len(set(dirs)) > max_lines:
            lines.append("  ...")
    return _pad_art(lines)


def render_scanning_seed(*, color: str = "yellow") -> list[str]:
    """Placeholder art before symbols appear."""
    lines = [
        f"[{color}]scanning[/]",
        f"[dim]symbols…[/dim]",
    ]
    return _pad_art(lines)


def render_labeled_graph(
    nodes: Sequence[dict[str, Any]],
    edges: Sequence[tuple[int, int]],
    *,
    cols: int = ART_COLS,
    rows: int = ART_ROWS,
    color: str = "cyan",
    expansion: float = 1.0,
    settled: bool = False,
) -> list[str]:
    """Render a neofetch-scale graph with word labels and animated arc edges."""
    grid = _build_graph_grid(nodes, edges, cols=cols, rows=rows, expansion=expansion)
    return _grid_to_lines(grid, color=color, settled=settled)


def _build_graph_grid(
    nodes: Sequence[dict[str, Any]],
    edges: Sequence[tuple[int, int]],
    *,
    cols: int,
    rows: int,
    expansion: float,
) -> list[list[str]]:
    grid = [[" " for _ in range(cols)] for _ in range(rows)]

    if not nodes:
        inner_mid = rows // 2
        inner_col = cols // 2
        seed = "·" if expansion < 0.2 else "graph"
        grid[inner_mid][max(0, inner_col - len(seed) // 2)] = seed
        return grid

    hubs, slot_for = _select_hubs(nodes, edges)
    if not hubs:
        return grid

    t = ease_out_cubic(expansion)
    label_alpha = ease_out_cubic(max(0.0, (expansion - 0.05) / 0.4))
    edge_strength = ease_out_cubic(max(0.0, (expansion - 0.2) / 0.8))

    anchors: dict[int, tuple[int, int]] = {}
    labels: dict[int, str] = {}
    for node in hubs:
        nid = node["id"]
        slot = slot_for[nid]
        tx, ty = HUB_SLOTS[slot]
        cx = int(_CENTER[0] + (tx - _CENTER[0]) * t)
        cy = int(_CENTER[1] + (ty - _CENTER[1]) * t)
        label = _short_label(str(node.get("name", nid)))
        labels[nid] = label
        anchors[nid] = (cx, cy)
        if label_alpha > 0.15:
            chars = max(1, int(len(label) * min(1.0, label_alpha)))
            _write_label(grid, label[:chars], cx, cy, cols, rows)

    if edge_strength > 0.05:
        hub_ids = list(anchors.keys())
        hub_edges = _select_hub_edges(hub_ids, edges, degree_hint=_hub_degrees(hubs, edges))
        for edge_idx, (src, tgt) in enumerate(hub_edges):
            lane = (edge_idx % 3) - 1
            _draw_routed_edge(
                grid,
                anchors[src],
                labels[src],
                anchors[tgt],
                labels[tgt],
                strength=edge_strength,
                cols=cols,
                rows=rows,
                lane=lane,
            )

    return grid


def _hub_degrees(
    hubs: Sequence[dict[str, Any]],
    edges: Sequence[tuple[int, int]],
) -> dict[int, int]:
    hub_ids = {n["id"] for n in hubs}
    degree = {n["id"]: 0 for n in hubs}
    for src, tgt in edges:
        if src in hub_ids and tgt in hub_ids:
            degree[src] += 1
            degree[tgt] += 1
    return degree


def _select_hub_edges(
    hub_ids: Sequence[int],
    edges: Sequence[tuple[int, int]],
    *,
    degree_hint: dict[int, int],
    max_edges: int = MAX_HUB_EDGES,
) -> list[tuple[int, int]]:
    """Pick edges that connect every visible hub; prefer high-degree links."""
    hub_set = set(hub_ids)
    if len(hub_set) < 2:
        return []

    candidates: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for src, tgt in edges:
        if src not in hub_set or tgt not in hub_set or src == tgt:
            continue
        key = (min(src, tgt), max(src, tgt))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(key)

    def weight(edge: tuple[int, int]) -> int:
        a, b = edge
        return degree_hint.get(a, 0) + degree_hint.get(b, 0)

    candidates.sort(key=weight, reverse=True)

    parent = {hid: hid for hid in hub_set}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    selected: list[tuple[int, int]] = []
    for edge in candidates:
        a, b = edge
        if find(a) != find(b):
            selected.append(edge)
            union(a, b)

    # Spoke isolated hubs to the primary (highest-degree) node.
    primary = max(hub_set, key=lambda hid: degree_hint.get(hid, 0))
    for hid in hub_set:
        if find(hid) != find(primary):
            selected.append((min(hid, primary), max(hid, primary)))
            union(hid, primary)

    for edge in candidates:
        if edge not in selected and len(selected) < max_edges:
            selected.append(edge)

    return selected[:max_edges]


def _select_hubs(
    nodes: Sequence[dict[str, Any]],
    edges: Sequence[tuple[int, int]],
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    if not nodes:
        return [], {}

    degree: dict[int, int] = {n["id"]: 0 for n in nodes}
    for src, tgt in edges:
        if src in degree:
            degree[src] += 1
        if tgt in degree:
            degree[tgt] += 1

    ranked = sorted(nodes, key=lambda n: (-degree.get(n["id"], 0), str(n.get("name", ""))))
    hubs = ranked[: min(MAX_HUBS, len(HUB_SLOTS))]
    slot_for = {hub["id"]: idx for idx, hub in enumerate(hubs)}
    return hubs, slot_for


def _short_label(name: str) -> str:
    if "::" in name:
        name = name.rsplit("::", 1)[-1]
    if "." in name:
        tail = name.rsplit(".", 1)[-1]
        if tail and not tail.startswith("Test"):
            name = tail
    name = name.lstrip("_")
    if len(name) > LABEL_MAX and "_" in name:
        parts = [p for p in name.split("_") if len(p) >= 3]
        if parts:
            name = max(parts, key=len)
    if len(name) > LABEL_MAX:
        name = name[:LABEL_MAX]
    return name or "?"


def _write_label(
    grid: list[list[str]],
    label: str,
    anchor_col: int,
    row: int,
    cols: int,
    rows: int,
) -> None:
    start_col = max(0, min(cols - len(label), anchor_col - len(label) // 2))
    if row < 0 or row >= rows:
        return
    for i, ch in enumerate(label):
        c = start_col + i
        if 0 <= c < cols:
            grid[row][c] = ch


def _label_bounds(
    anchor_col: int, row: int, label: str, cols: int, rows: int
) -> tuple[int, int, int, int]:
    start_col = max(0, min(cols - len(label), anchor_col - len(label) // 2))
    end_col = start_col + len(label) - 1
    return start_col, row, end_col, row


def _connection_point(
    anchor: tuple[int, int],
    label: str,
    toward: tuple[int, int],
    *,
    cols: int,
    rows: int,
) -> tuple[int, int]:
    """Edge attach point just outside the label box."""
    col, row = anchor
    tc, tr = toward
    left, top, right, bottom = _label_bounds(col, row, label, cols, rows)
    if tr > bottom:
        return (max(left, min(right, tc)), bottom + 1)
    if tr < top:
        return (max(left, min(right, tc)), top - 1)
    if tc > right:
        return (right + 1, max(top, min(bottom, tr)))
    if tc < left:
        return (left - 1, max(top, min(bottom, tr)))
    return anchor


def _draw_routed_edge(
    grid: list[list[str]],
    anchor_a: tuple[int, int],
    label_a: str,
    anchor_b: tuple[int, int],
    label_b: str,
    *,
    strength: float,
    cols: int,
    rows: int,
    lane: int = 0,
) -> None:
    """Manhattan route between labels; vertical legs avoid label cells."""
    x0, y0 = _connection_point(anchor_a, label_a, anchor_b, cols=cols, rows=rows)
    x1, y1 = _connection_point(anchor_b, label_b, anchor_a, cols=cols, rows=rows)
    mid_y = (y0 + y1) // 2 + lane
    mid_y = max(0, min(rows - 1, mid_y))

    path: list[tuple[int, int, str]] = []
    for y in _line_range(y0, mid_y):
        path.append((x0, y, "│"))
    for x in _line_range(x0, x1):
        if x != x0 or mid_y != y0:
            path.append((x, mid_y, "─"))
    for y in _line_range(mid_y, y1):
        path.append((x1, y, "│"))

    if x0 != x1 and y0 != mid_y:
        path.append((x0, mid_y, _corner_char(x0, x1, y0, mid_y)))
    if x1 != x0 and y1 != mid_y:
        path.append((x1, mid_y, _corner_char(x1, x0, mid_y, y1)))

    limit = max(1, int(len(path) * strength))
    for x, y, ch in path[:limit]:
        if not (0 <= x < cols and 0 <= y < rows):
            continue
        if _is_label(grid[y][x]):
            continue
        if grid[y][x] in _EDGE_CHARS or grid[y][x] == " ":
            grid[y][x] = ch


def _is_label(ch: str) -> bool:
    return ch not in _EDGE_CHARS and ch != " "


def _corner_char(x_from: int, x_to: int, y_from: int, y_to: int) -> str:
    right = x_to > x_from
    down = y_to > y_from
    if right and down:
        return "┌"
    if not right and down:
        return "┐"
    if right and not down:
        return "└"
    return "┘"


def _line_range(a: int, b: int):
    if a <= b:
        return range(a, b + 1)
    return range(a, b - 1, -1)


def _grid_to_lines(grid: list[list[str]], *, color: str = "cyan", settled: bool = False) -> list[str]:
    node_color = color
    edge_style = "bright_black" if settled else "cyan"
    corner_chars = "┌┐└┘"
    lines: list[str] = []
    for row in grid:
        parts: list[str] = []
        for ch in row:
            if ch in "─│╲╱" or ch in corner_chars:
                parts.append(f"[{edge_style}]{ch}[/{edge_style}]")
            elif ch == " ":
                parts.append(" ")
            else:
                parts.append(f"[bold {node_color}]{ch}[/bold {node_color}]")
        lines.append("".join(parts))
    return lines


def _pad_art(lines: list[str], rows: int = ART_ROWS) -> list[str]:
    if len(lines) >= rows:
        return lines[:rows]
    return lines + [" "] * (rows - len(lines))