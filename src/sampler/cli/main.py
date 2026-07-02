import sys
from pathlib import Path

import typer
from rich.console import Console

from sampler import __version__
from sampler.config import ConfigManager
from sampler.db import Database
from sampler.query.engine import QueryEngine

# Embeddings provider support (lazy, optional)
try:
    from sampler.embeddings import get_embedding_provider
except Exception:
    get_embedding_provider = None  # type: ignore

app = typer.Typer(help="Sampler CLI", no_args_is_help=True)
project_app = typer.Typer(help="Project management commands")
app.add_typer(project_app, name="project")

config_app = typer.Typer(help="Configuration commands (global ~/.sampler/config.yaml)")
app.add_typer(config_app, name="config")
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"sampler {__version__}")
        raise typer.Exit()


@app.callback()
def app_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show sampler version and exit.",
    ),
) -> None:
    """Sampler CLI root callback."""


def _database() -> Database:
    cfg = ConfigManager().load()
    db_path = Path(cfg.cache_dir).expanduser() / "graph.db"
    db = Database(db_path=db_path)
    db.init_schema()
    return db


def _get_project_roots() -> dict[str, Path]:
    """Map project name -> absolute root path for relative path computation."""
    config = ConfigManager()
    roots: dict[str, Path] = {}
    for p in config.list_projects():
        try:
            roots[p.name] = Path(p.path).expanduser().resolve()
        except Exception:
            pass
    return roots


def _short_path(project_name: str, full_path: str, roots: dict[str, Path]) -> str:
    """Return shortest useful path for display: relative to project root if possible, else tail or name."""
    root = roots.get(project_name)
    if root:
        try:
            return str(Path(full_path).resolve().relative_to(root))
        except Exception:
            pass
    # Fallback: last 1-2 path segments to keep output short (token friendly)
    p = Path(full_path)
    if len(p.parts) >= 3:
        return "/".join(p.parts[-2:])
    return p.name


def _format_line_range(start_line: int | None, end_line: int | None) -> str:
    """Format a symbol's line range compactly: 'start-end' when both known, else 'start' or '-'."""
    if not start_line:
        return "-"
    if end_line and end_line != start_line:
        return f"{start_line}-{end_line}"
    return str(start_line)


@app.command("version")
def version(
    plain: bool = typer.Option(False, "--plain", help="Plain text output (version number only)"),
) -> None:
    """Show installed sampler version."""
    if plain or not sys.stdout.isatty():
        console.print(f"sampler {__version__}")
        return

    from sampler.viz.headline import print_version_card

    print_version_card(console, __version__)


@app.command("init")
def init() -> None:
    """Initialize sampler local data directory."""
    config = ConfigManager()
    config.load()
    data_dir = Path.home() / ".sampler"
    console.print(f"Initialized [bold]{data_dir}[/bold]")


# --- Config commands (embeddings provider etc.) ---

@config_app.command("show")
def config_show() -> None:
    """Show current global configuration (including embeddings provider)."""
    cfg = ConfigManager().load()
    console.print(f"[bold]cache_dir:[/bold] {cfg.cache_dir}")
    console.print(f"[bold]version:[/bold] {cfg.version}")
    emb = cfg.embeddings
    console.print("\n[bold]embeddings:[/bold]")
    console.print(f"  provider: [cyan]{emb.provider}[/cyan]")
    if emb.model:
        console.print(f"  model: {emb.model}")
    if emb.base_url:
        console.print(f"  base_url: {emb.base_url}")
    console.print("\n[dim]Edit ~/.sampler/config.yaml directly or use 'sampler config embeddings ...'[/dim]")


@config_app.command("embeddings")
def config_embeddings(
    provider: str | None = typer.Option(None, "--provider", "-p", help="bge-small | hash | ollama | nomic | openai | fastembed"),
    model: str | None = typer.Option(None, "--model", "-m", help="model name for ollama/nomic/openai (e.g. nomic-embed-text)"),
    base_url: str | None = typer.Option(None, "--base-url", help="Ollama URL or compatible endpoint"),
) -> None:
    """Get or set the embeddings provider configuration.

    Examples:
      sampler config embeddings --provider bge-small
      sampler config embeddings --provider ollama --model nomic-embed-text
      sampler config embeddings --provider hash          # offline / no ML deps
    """
    cm = ConfigManager()
    if provider is None and model is None and base_url is None:
        # Show current
        emb = cm.get_embeddings_config()
        console.print(f"provider: [cyan]{emb.provider}[/cyan]")
        if emb.model:
            console.print(f"model: {emb.model}")
        if emb.base_url:
            console.print(f"base_url: {emb.base_url}")
        return

    updated = cm.update_embeddings(provider=provider, model=model, base_url=base_url)
    console.print("[green]✓[/green] Embeddings config updated:")
    console.print(f"  provider: [cyan]{updated.provider}[/cyan]")
    if updated.model:
        console.print(f"  model: {updated.model}")
    if updated.base_url:
        console.print(f"  base_url: {updated.base_url}")
    console.print("\n[dim]Run 'sampler embed <project>' to precompute vectors for the new provider.[/dim]")


@project_app.command("list")
def project_list() -> None:
    """List registered projects (clean table view)."""
    config = ConfigManager()
    projects = config.list_projects()
    home = str(Path.home().resolve())

    if not projects:
        console.print("[dim]No projects registered. Use 'sampler project add <name> <path> --language auto'[/dim]")
        return

    # Rich table = much cleaner output
    from rich.table import Table

    table = Table(title="Projects", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Path")
    table.add_column("Language", style="green")
    table.add_column("Enabled", justify="center")

    db = _database()

    for p in projects:
        try:
            pp = Path(p.path).resolve()
            ps = str(pp)
            if ps.startswith(home):
                disp = "~" + ps[len(home):]
            else:
                parts = pp.parts
                disp = "/".join(parts[-2:]) if len(parts) > 2 else ps
        except Exception:
            disp = p.path
        enabled = "[green]yes[/green]" if p.enabled else "[dim]no[/dim]"

        lang_display = p.language
        if (p.language or "").lower() == "auto":
            breakdown = db.get_project_language_breakdown(p.name)
            total = sum(breakdown.values()) or 1
            parts = []
            for lang, cnt in sorted(breakdown.items(), key=lambda kv: -kv[1])[:4]:  # top 4 for brevity
                pct = int(round(cnt * 100 / total))
                parts.append(f"{lang} {pct}%")
            if parts:
                lang_display = f"auto ({', '.join(parts)})"
            else:
                lang_display = "auto (no files yet)"

        table.add_row(p.name, disp, lang_display, enabled)

    console.print(table)


@project_app.command("add")
def project_add(
    name: str,
    path: str,
    language: str = typer.Option(
        "python", "--language", help="python, go, typescript, javascript, vue, or 'auto' for monorepos"
    ),
) -> None:
    """Register project in global config."""
    config = ConfigManager()
    try:
        project = config.add_project(name=name, path=path, language=language)
    except ValueError as exc:
        raise typer.BadParameter(f"{exc}\nTip: Use an absolute path that exists.") from exc
    console.print(f"Added project [bold]{project.name}[/bold]")


@project_app.command("remove")
def project_remove(name: str) -> None:
    """Remove project from global config."""
    config = ConfigManager()
    try:
        config.remove_project(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Removed project [bold]{name}[/bold]")


@project_app.command("update")
def project_update(
    name: str,
    path: str | None = typer.Option(None, "--path", help="New absolute path for the project"),
    language: str | None = typer.Option(None, "--language", help="New language (python|go|typescript|javascript|vue|auto)"),
) -> None:
    """Update a registered project's path/language in place (no remove/add needed)."""
    if path is None and language is None:
        raise typer.BadParameter("Provide at least one of --path or --language to update.")
    config = ConfigManager()
    try:
        project = config.update_project(name, path=path, language=language)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"Updated project [bold]{project.name}[/bold]: path={project.path} language={project.language}")
    console.print(f"Tip: run 'sampler index {project.name}' to re-index with the updated settings.")


@project_app.command("deps")
def project_deps(name: str) -> None:
    """Show cross-project dependencies detected for a project (via import resolution)."""
    config = ConfigManager()
    if config.get_project(name) is None:
        raise typer.BadParameter(
            f"Project '{name}' not found.\nUse 'sampler project list' to see registered projects."
        )

    rows = _database().get_project_dependencies(name)
    if not rows:
        console.print(f"No cross-project dependencies found for '{name}'.")
        console.print("Tip: dependencies are detected during 'sampler index <project>' via import resolution.")
        return

    for r in rows:
        if r["source_project"] == name:
            console.print(f"{name} -> {r['target_project']}  [{r['type']}]")
        else:
            console.print(f"{name} <- {r['source_project']}  [{r['type']}]")


@app.command("search")
def search(
    query: str,
    project: str | None = typer.Option(None, "--project", "-p"),
    type: str | None = typer.Option(None, "--type", "-t", help="filter e.g. function,class"),
    limit: int = typer.Option(10, "--limit", "-l"),
    semantic: bool = typer.Option(
        False, "--semantic", help="Hybrid semantic+graph ranking (requires 'sampler embed <project>' first)"
    ),
    style: str = typer.Option("plain", "--style", help="'plain' (default) or 'bars' (colored relationship view)"),
) -> None:
    """Search symbols by name (or --semantic for meaning-based hybrid search)."""
    if semantic:
        if not project:
            raise typer.BadParameter("--semantic requires --project <name>.")
        from sampler.query.semantic import SemanticEngine

        try:
            results = SemanticEngine(db=_database()).hybrid_search(query=query, project_name=project, limit=limit)
        except RuntimeError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if not results:
            console.print(f"No semantic matches found for project '{project}'.")
            return
        roots = _get_project_roots()
        for r in results:
            line = _format_symbol_line(r, roots)
            score = r.get("score", 0.0)
            console.print(f"{line}  [yellow]score={score:.3f}[/yellow]")
        return

    engine = QueryEngine(db=_database())
    types = [x.strip() for x in type.split(",")] if type else None
    if types:
        exp = set(types)
        for t in list(types):
            if t == "function": exp.add("async function")
            elif t == "method": exp.add("async method")
        types = list(exp)
    rows = engine.search(query=query, project_name=project, types=types, limit=limit)
    roots = _get_project_roots()

    def _line(r: dict) -> str:
        shortf = _short_path(r["project_name"], r["file_path"], roots)
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        # Cleaner + rich markup: dim path, bold name, colored type
        type_col = "green" if "function" in (r.get("type") or "") else "blue" if "class" in (r.get("type") or "") else "cyan"
        text = (
            f"[dim]{r['project_name']}[/]:[dim]{shortf}:{r['start_line'] or '-'}[/] "
            f"[{type_col}]{r['type']}[/] [bold]{name}[/bold]"
        )
        if sig:
            text += f"  [dim]{sig}[/dim]"
        return text

    if style == "bars":
        from sampler.cli.render import render_bars

        edges = engine.relationships_among(rows)
        render_bars(console, rows, edges, _line)
        return

    for r in rows:
        console.print(_line(r))


@app.command("search-all")
def search_all(
    query: str,
    type: str | None = typer.Option(None, "--type", "-t", help="filter e.g. function,class"),
    limit: int = typer.Option(100, "--limit", "-l"),
) -> None:
    """Search symbols across ALL projects."""
    search(query=query, project=None, type=type, limit=limit)


@app.command("symbols")
def symbols(
    project: str,
    type: str | None = typer.Option(None, "--type", "-t", help="filter e.g. function,class"),
    limit: int = typer.Option(100, "--limit", "-l"),
) -> None:
    """List all symbols for a project (useful for getting a quick overview)."""
    config = ConfigManager()
    if config.get_project(project) is None:
        raise typer.BadParameter(
            f"Project '{project}' not found.\n"
            f"Run: sampler project add {project} <absolute/path> --language python\n"
            "Use 'sampler project list' to see registered projects."
        )

    engine = QueryEngine(db=_database())
    types = [x.strip() for x in type.split(",")] if type else None
    if types:
        exp = set(types)
        for t in list(types):
            if t == "function":
                exp.add("async function")
            elif t == "method":
                exp.add("async method")
        types = list(exp)

    rows = engine.list_symbols(project_name=project, types=types, limit=limit)
    roots = _get_project_roots()

    for r in rows:
        shortf = _short_path(r["project_name"], r["file_path"], roots)
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        lines = _format_line_range(r["start_line"], r["end_line"])
        type_col = "green" if "function" in (r.get("type") or "") else "blue" if "class" in (r.get("type") or "") else "cyan"
        line = (
            f"[dim]{r['project_name']}[/]:[dim]{shortf}:{lines}[/] "
            f"[{type_col}]{r['type']}[/] [bold]{name}[/bold]"
        )
        if sig:
            line += f"  [dim]{sig}[/dim]"
        console.print(line)


def _build_embedder():
    from sampler.indexer.embedder import Embedder

    if get_embedding_provider is not None:
        try:
            return Embedder(provider=get_embedding_provider())
        except Exception:
            return Embedder()
    return Embedder()


@app.command("index")
def index(
    project: str,
    plain: bool = typer.Option(False, "--plain", help="Compact output without Live visualization (for CI/scripts)"),
    batch_size: int = typer.Option(32, "--batch-size", help="Batch size for embedding generation"),
    force: bool = typer.Option(False, "--force", help="Re-index all files regardless of hash"),
) -> None:
    """Index project and generate embeddings (Live visualization when attached to a TTY)."""
    config = ConfigManager()
    project_cfg = config.get_project(project)
    if project_cfg is None:
        raise typer.BadParameter(
            f"Project '{project}' not found.\n"
            f"Run: sampler project add {project} <absolute/path> --language python\n"
            "Then: sampler index {project}\n"
            "Use 'sampler project list' to see registered projects."
        )

    embedder = _build_embedder()
    use_plain = plain or not sys.stdout.isatty()

    try:
        embedder.provider.embed("sampler health probe", for_query=True)
    except RuntimeError as exc:
        from rich.panel import Panel

        console.print(Panel.fit(str(exc), title="Error", border_style="red"))
        raise typer.Exit(code=1)

    from sampler.viz.pipeline import run_index_pipeline

    try:
        stats = run_index_pipeline(
            db=_database(),
            project_cfg=project_cfg,
            embedder=embedder,
            force=force,
            batch_size=batch_size,
            plain=use_plain,
            console=console,
        )
    except RuntimeError as exc:
        from rich.panel import Panel

        console.print(Panel.fit(str(exc), title="Error", border_style="red"))
        raise typer.Exit(code=1)

    if use_plain:
        console.print(
            f"[green]✓[/green] Indexed [bold]{stats['project']}[/bold]: "
            f"discovered={stats['discovered']} indexed={stats['indexed']} "
            f"skipped={stats['skipped']} failed={stats['failed']}"
        )
        prov_name = getattr(embedder.provider, "name", "hash")
        console.print(
            f"[green]✓[/green] Embedded [bold]{stats['embed_count']}[/bold] symbols "
            f"using [bold]{prov_name}[/bold] ({stats['model']}) in [bold]{stats['elapsed']:.1f}s[/bold]"
        )


@app.command("embed")
def embed(
    project: str,
    batch_size: int = typer.Option(32, "--batch-size", help="Batch size for embedding generation"),
) -> None:
    """Generate/refresh embeddings for symbols using the configured provider (default: bge-small).

    Pre-computed embeddings power `search --semantic`. Run after `index` (or when provider changes).
    """
    config = ConfigManager()
    if config.get_project(project) is None:
        raise typer.BadParameter(
            f"Project '{project}' not found.\n"
            f"Run: sampler project add {project} <absolute/path> --language python\n"
            "Use 'sampler project list' to see registered projects."
        )

    from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn

    from sampler.indexer.embedder import Embedder

    # Respect current embeddings config (bge-small, ollama, hash, ...)
    if get_embedding_provider is not None:
        try:
            provider = get_embedding_provider()
            embedder = Embedder(provider=provider)
        except RuntimeError as e:
            from rich.panel import Panel

            console.print(Panel.fit(str(e), title="Error", border_style="red"))
            raise typer.Exit(code=1)
    else:
        embedder = Embedder()

    prov_name = getattr(embedder.provider, "name", "hash")
    model_id = getattr(embedder.provider, "model_id", embedder.backend)

    # Preflight provider before showing progress; avoids odd 0/? bar + usage error for missing deps.
    try:
        embedder.provider.embed("sampler health probe", for_query=True)
    except RuntimeError as exc:
        from rich.panel import Panel

        console.print(Panel.fit(str(exc), title="Error", border_style="red"))
        raise typer.Exit(code=1)

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Embedding {project} ({prov_name})", total=None)

            def _on_progress(done: int, total: int) -> None:
                if progress.tasks[task].total is None:
                    progress.update(task, total=total)
                progress.update(task, completed=done)

            count = embedder.embed_project(
                db=_database(), project_name=project, batch_size=batch_size, on_progress=_on_progress
            )
    except RuntimeError as exc:
        from rich.panel import Panel

        console.print(Panel.fit(str(exc), title="Error", border_style="red"))
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓[/green] Embedded [bold]{count}[/bold] symbols for [bold]{project}[/bold] "
        f"using [bold]{prov_name}[/bold] ({model_id})"
    )


@app.command("overview")
def overview(
    filepath: str,
    style: str = typer.Option("plain", "--style", help="'plain' (default) or 'bars' (colored relationship view)"),
) -> None:
    """Show symbols for a file.

    Supports absolute and relative paths.
    Relative paths are first resolved from cwd; if nothing matches we also try
    resolving relative to each registered project's root (very convenient).
    """
    config = ConfigManager()
    projects = config.list_projects()

    candidates = []
    try:
        candidates.append(str(Path(filepath).resolve()))
    except Exception:
        candidates.append(filepath)

    # Try resolving relative to each project root (helps when you're inside the project)
    for p in projects:
        try:
            root = Path(p.path).resolve()
            rel = root / filepath
            candidates.append(str(rel.resolve()))
        except Exception:
            pass

    # Dedup while preserving order
    seen = set()
    candidates = [c for c in candidates if not (c in seen or seen.add(c))]

    engine = QueryEngine(db=_database())
    rows = []
    matched_path = None
    for cand in candidates:
        rows = engine.overview(filepath=cand)
        if rows:
            matched_path = cand
            break

    if not rows:
        console.print(f"No symbols found for file: {filepath}")
        console.print("Tip: Make sure the project is registered with 'sampler project add' and indexed with 'sampler index <project>'.")
        return

    def _line(r: dict) -> str:
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        lines = _format_line_range(r["start_line"], r["end_line"])
        type_col = "green" if "function" in (r.get("type") or "") else "blue" if "class" in (r.get("type") or "") else "cyan"
        text = f"{lines}: [{type_col}]{r['type']}[/] [bold]{name}[/bold]"
        if sig:
            text += f"  [dim]{sig}[/dim]"
        return text

    if style == "bars":
        from sampler.cli.render import render_bars

        edges = engine.relationships_among(rows)
        render_bars(console, rows, edges, _line)
        return

    for r in rows:
        console.print(_line(r))


def _format_symbol_line(r: dict, roots: dict[str, Path]) -> str:
    shortf = _short_path(r["project_name"], r["file_path"], roots)
    name = r["qualified_name"] or r["name"]
    lines = _format_line_range(r["start_line"], r["end_line"])
    type_col = "green" if "function" in (r.get("type") or "") else "blue" if "class" in (r.get("type") or "") else "cyan"
    return (
        f"[dim]{r['project_name']}[/]:[dim]{shortf}:{lines}[/] "
        f"[{type_col}]{r['type']}[/] [bold]{name}[/bold]"
    )


def _resolve_or_report(
    matches: list[dict],
    symbol: str,
    roots: dict[str, Path],
    project: str | None = None,
    file_path: str | None = None,
) -> bool:
    """Print an error/disambiguation message when matches != 1. Returns True if safe to proceed."""
    if len(matches) == 0:
        console.print(f"No symbol found matching '{symbol}'.")
        console.print("Tip: use 'sampler search <name> --project <project>' to find the right name.")
        return False
    if len(matches) > 1:
        console.print(f"Ambiguous symbol '{symbol}', found {len(matches)} matches:")
        for m in matches:
            console.print(f"  {_format_symbol_line(m, roots)}")
        if file_path:
            console.print("Tip: --file is set but still ambiguous. Use a more specific file path.")
        elif project:
            console.print("Tip: narrow down with --file <path/suffix>.")
        else:
            console.print("Tip: narrow down with --project <project> and/or --file <path/suffix>.")
        return False
    return True


def _parse_symbol_selector(symbol: str, file_path: str | None) -> tuple[str, str | None]:
    """Accept optional selector format 'path/to/file.py:symbol_name'.

    Explicit --file always wins. If --file is absent and selector syntax is
    present, split on the last ':' so path segments can still contain ':'.
    """
    if file_path:
        return symbol, file_path
    if ":" not in symbol:
        return symbol, None
    left, right = symbol.rsplit(":", 1)
    if left.strip() and right.strip():
        return right.strip(), left.strip()
    return symbol, file_path


@app.command("callers")
def callers(
    symbol: str,
    project: str | None = typer.Option(None, "--project", "-p"),
    file: str | None = typer.Option(None, "--file", "-f", help="Disambiguate by file path (absolute or suffix)"),
) -> None:
    """Show symbols that CALL the given symbol."""
    engine = QueryEngine(db=_database())
    symbol, file = _parse_symbol_selector(symbol, file)
    matches, rows = engine.callers(symbol, project, file)
    roots = _get_project_roots()
    if not _resolve_or_report(matches, symbol, roots, project=project, file_path=file):
        return
    if not rows:
        console.print(f"No callers found for {symbol}.")
        return
    for r in rows:
        console.print(_format_symbol_line(r, roots))


@app.command("usages")
def usages(
    symbol: str,
    project: str | None = typer.Option(None, "--project", "-p"),
    file: str | None = typer.Option(None, "--file", "-f", help="Disambiguate by file path (absolute or suffix)"),
) -> None:
    """Show symbols that reference the given symbol (any relationship type, broader than callers)."""
    engine = QueryEngine(db=_database())
    symbol, file = _parse_symbol_selector(symbol, file)
    matches, rows = engine.usages(symbol, project, file)
    roots = _get_project_roots()
    if not _resolve_or_report(matches, symbol, roots, project=project, file_path=file):
        return
    if not rows:
        console.print(f"No usages found for {symbol}.")
        return
    for r in rows:
        console.print(f"{_format_symbol_line(r, roots)}  [magenta][{r['relation_type']}][/magenta]")


@app.command("related")
def related(
    symbol: str,
    project: str | None = typer.Option(None, "--project", "-p"),
    file: str | None = typer.Option(None, "--file", "-f", help="Disambiguate by file path (absolute or suffix)"),
    style: str = typer.Option("plain", "--style", help="'plain' (default) or 'bars' (colored relationship view)"),
) -> None:
    """Show symbols related via CONTAINS (parent class / child methods)."""
    engine = QueryEngine(db=_database())
    symbol, file = _parse_symbol_selector(symbol, file)
    matches, rows = engine.related(symbol, project, file)
    roots = _get_project_roots()
    if not _resolve_or_report(matches, symbol, roots, project=project, file_path=file):
        return
    if not rows:
        console.print(f"No related symbols found for {symbol}.")
        return

    if style == "bars":
        from sampler.cli.render import render_bars

        edges = engine.relationships_among(rows)
        render_bars(console, rows, edges, lambda r: f"{_format_symbol_line(r, roots)}  [{r['relation']}]")
        return

    for r in rows:
        console.print(f"{_format_symbol_line(r, roots)}  [magenta][{r['relation']}][/magenta]")


@app.command("stale-code")
def stale_code(
    project: str,
    limit: int = typer.Option(100, "--limit", "-l"),
) -> None:
    """Detect likely stale functions: called by tests but not by non-test code."""
    config = ConfigManager()
    if config.get_project(project) is None:
        raise typer.BadParameter(
            f"Project '{project}' not found.\nUse 'sampler project list' to see registered projects."
        )

    engine = QueryEngine(db=_database())
    rows = engine.stale_code_candidates(project)
    if not rows:
        console.print(f"No stale-code candidates found for {project}.")
        return

    roots = _get_project_roots()
    for r in rows[:limit]:
        callers = ", ".join(r["test_callers"][:3])
        if len(r["test_callers"]) > 3:
            callers += ", ..."
        line = _format_symbol_line(r, roots)
        console.print(
            f"{line}  [yellow]test={r['test_caller_count']}[/] "
            f"[dim]non_test={r['non_test_caller_count']}[/]  [dim]{callers}[/dim]"
        )


if __name__ == "__main__":
    app()
