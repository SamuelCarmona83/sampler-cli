from __future__ import annotations

import math
import random
from typing import Sequence

CENTER = (50.0, 50.0)
SQUARE = 100.0


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_sine(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def radial_layout(
    node_ids: Sequence[int],
    *,
    center: tuple[float, float] = CENTER,
    radius: float = 38.0,
) -> dict[int, tuple[float, float]]:
    """Place nodes evenly on a circle — stable targets for center-out expansion."""
    if not node_ids:
        return {}
    n = len(node_ids)
    out: dict[int, tuple[float, float]] = {}
    for i, nid in enumerate(node_ids):
        angle = (2.0 * math.pi * i / n) - math.pi / 2.0
        out[nid] = (
            center[0] + radius * math.cos(angle),
            center[1] + radius * math.sin(angle),
        )
    return out


def expand_from_center(
    targets: dict[int, tuple[float, float]],
    expansion: float,
    *,
    center: tuple[float, float] = CENTER,
) -> dict[int, tuple[float, float]]:
    """Interpolate every node from center toward its target with easing."""
    t = ease_out_cubic(expansion)
    return {
        nid: (
            center[0] + (tx - center[0]) * t,
            center[1] + (ty - center[1]) * t,
        )
        for nid, (tx, ty) in targets.items()
    }


def fruchterman_reingold(
    node_ids: Sequence[int],
    edges: Sequence[tuple[int, int]],
    *,
    size: float = SQUARE,
    iterations: int = 40,
    seed: int = 42,
) -> dict[int, tuple[float, float]]:
    """Force-directed layout constrained to a square."""
    if not node_ids:
        return {}

    width = height = size
    rng = random.Random(seed)
    n = len(node_ids)
    area = width * height
    k = math.sqrt(area / max(n, 1))
    temperature = width / 12.0
    cooling = temperature / max(iterations, 1)

    margin = 12.0
    pos: dict[int, tuple[float, float]] = {
        nid: (rng.uniform(margin, width - margin), rng.uniform(margin, height - margin))
        for nid in node_ids
    }

    for _ in range(iterations):
        disp: dict[int, list[float]] = {nid: [0.0, 0.0] for nid in node_ids}

        for i, v in enumerate(node_ids):
            for u in node_ids[i + 1 :]:
                dx = pos[v][0] - pos[u][0]
                dy = pos[v][1] - pos[u][1]
                dist = math.hypot(dx, dy)
                if dist < 1e-6:
                    dist = 1e-6
                    dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
                force = (k * k) / dist
                disp[v][0] += (dx / dist) * force
                disp[v][1] += (dy / dist) * force
                disp[u][0] -= (dx / dist) * force
                disp[u][1] -= (dy / dist) * force

        for src, tgt in edges:
            if src not in pos or tgt not in pos:
                continue
            dx = pos[src][0] - pos[tgt][0]
            dy = pos[src][1] - pos[tgt][1]
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                dist = 1e-6
            force = (dist * dist) / k
            disp[src][0] -= (dx / dist) * force
            disp[src][1] -= (dy / dist) * force
            disp[tgt][0] += (dx / dist) * force
            disp[tgt][1] += (dy / dist) * force

        for nid in node_ids:
            dx, dy = disp[nid]
            dist = math.hypot(dx, dy)
            if dist > temperature:
                dx = dx / dist * temperature
                dy = dy / dist * temperature
            pos[nid] = (
                min(width - margin, max(margin, pos[nid][0] + dx)),
                min(height - margin, max(margin, pos[nid][1] + dy)),
            )

        temperature = max(0.0, temperature - cooling)

    return pos


def blend_positions(
    current: dict[int, tuple[float, float]],
    target: dict[int, tuple[float, float]],
    alpha: float = 0.08,
) -> dict[int, tuple[float, float]]:
    """Gentle frame-by-frame blend when targets shift."""
    a = ease_in_out_sine(alpha)
    out: dict[int, tuple[float, float]] = {}
    for nid, (tx, ty) in target.items():
        cx, cy = current.get(nid, CENTER)
        out[nid] = (cx + (tx - cx) * a, cy + (ty - cy) * a)
    return out