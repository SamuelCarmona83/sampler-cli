from __future__ import annotations

from pathlib import Path

from sampler.viz.bus import EventBus, NullEventBus
from sampler.viz.events import DirDiscovered, FileDiscovered, Stage, StageChanged


def emit_discover(
    bus: EventBus | NullEventBus,
    project_path: str,
    file_entries: list[tuple[str, str]],
) -> None:
    bus.emit(StageChanged(Stage.DISCOVER))
    root = Path(project_path).resolve()
    dirs_seen: set[str] = set()
    total = len(file_entries)
    for idx, (filepath, _) in enumerate(file_entries):
        try:
            rel = Path(filepath).resolve().relative_to(root)
        except ValueError:
            rel = Path(filepath).name
        parts: list[str] = []
        for i, _part in enumerate(rel.parts[:-1]):
            parts.append("/".join(rel.parts[: i + 1]))
        for d in parts:
            if d not in dirs_seen:
                dirs_seen.add(d)
                bus.emit(DirDiscovered(d))
        bus.emit(FileDiscovered(path=filepath, index=idx, total=total))