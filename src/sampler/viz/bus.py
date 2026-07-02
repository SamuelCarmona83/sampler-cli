from __future__ import annotations

from collections.abc import Callable

from sampler.viz.events import IndexEvent


class EventBus:
    """Synchronous pub/sub for index pipeline events."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[IndexEvent], None]] = []

    def subscribe(self, handler: Callable[[IndexEvent], None]) -> None:
        self._handlers.append(handler)

    def emit(self, event: IndexEvent) -> None:
        for handler in self._handlers:
            handler(event)


class NullEventBus:
    """No-op bus for plain/headless indexing."""

    def subscribe(self, handler: Callable[[IndexEvent], None]) -> None:
        return None

    def emit(self, event: IndexEvent) -> None:
        return None