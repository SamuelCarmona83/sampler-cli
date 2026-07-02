from __future__ import annotations

from rich.console import Console

BRAND_TEXT = "SAMPLER"


def print_version_card(console: Console, version: str, *, animated: bool = True) -> None:
    """Neofetch-style version output: brand + compact facts."""
    del animated
    console.print(f"[bold cyan]{BRAND_TEXT}[/bold cyan]")
    console.print(f"[dim]version[/]  [bold]{version}[/]")
    console.print("[dim]index[/]     code → knowledge graph")
    console.print("[dim]search[/]    symbols · semantic · graph")