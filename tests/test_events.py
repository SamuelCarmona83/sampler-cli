from sampler.viz.bus import EventBus
from sampler.viz.events import FileDiscovered, Stage, StageChanged, SymbolExtracted


def test_event_bus_delivers_to_subscribers() -> None:
    bus = EventBus()
    seen: list[str] = []

    def handler(event) -> None:
        if isinstance(event, SymbolExtracted):
            seen.append(event.name)

    bus.subscribe(handler)
    bus.emit(StageChanged(Stage.PARSING))
    bus.emit(SymbolExtracted(name="foo", symbol_type="function"))
    bus.emit(FileDiscovered(path="/tmp/a.py", index=0, total=1))

    assert seen == ["foo"]