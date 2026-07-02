from __future__ import annotations

import threading
import time

from rich.console import Console
from rich.live import Live

from sampler.viz.bus import EventBus
from sampler.viz.engine import AnimationEngine

REFRESH_FPS = 12


class IndexLiveSession:
    """Rich Live wrapper that animates while the index pipeline runs."""

    def __init__(
        self,
        engine: AnimationEngine,
        bus: EventBus,
        *,
        console: Console | None = None,
    ) -> None:
        self.engine = engine
        self.bus = bus
        self.console = console or Console()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._live: Live | None = None

    def __enter__(self) -> IndexLiveSession:
        self.bus.subscribe(self.engine.handle)
        self._live = Live(
            self.engine.build_frame(),
            console=self.console,
            refresh_per_second=REFRESH_FPS,
            transient=False,
        )
        self._live.__enter__()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._live:
            self.engine.advance_frame()
            self._live.update(self.engine.build_frame())
            self._live.__exit__(exc_type, exc, tb)

    def _refresh_loop(self) -> None:
        interval = 1.0 / REFRESH_FPS
        while not self._stop.is_set():
            self.engine.advance_frame()
            if self._live:
                self._live.update(self.engine.build_frame())
            time.sleep(interval)