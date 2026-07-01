from pathlib import Path

import typer
from rich.console import Console

from sampler import __version__
from sampler.config import ConfigManager
from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.query.engine import QueryEngine

app = typer.Typer(help="Sampler CLI", no_args_is_help=True)
project_app = typer.Typer(help="Project management commands")
app.add_typer(project_app, name="project")
console = Console()


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
def version() -> None:
    """Show installed sampler version."""
    console.print(f"sampler {__version__}")


@app.command("init")
def init() -> None:
    """Initialize sampler local data directory."""
    config = ConfigManager()
    config.load()
    data_dir = Path.home() / ".sampler"
    console.print(f"Initialized [bold]{data_dir}[/bold]")


@project_app.command("list")
def project_list() -> None:
    """List registered projects."""
    config = ConfigManager()
    projects = config.list_projects()
    home = str(Path.home().resolve())

    for project in projects:
        try:
            pp = Path(project.path).resolve()
            ps = str(pp)
            if ps.startswith(home):
                disp = "~" + ps[len(home):]
            else:
                parts = pp.parts
                disp = "/".join(parts[-2:]) if len(parts) > 2 else ps
        except Exception:
            disp = project.path
        console.print(f"{project.name} {disp}")


@project_app.command("add")
def project_add(name: str, path: str, language: str = "python") -> None:
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
    language: str | None = typer.Option(None, "--language", help="New language (or 'auto' for monorepos)"),
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


@app.command("search")
def search(
    query: str,
    project: str | None = typer.Option(None, "--project", "-p"),
    type: str | None = typer.Option(None, "--type", "-t", help="filter e.g. function,class"),
    limit: int = typer.Option(100, "--limit", "-l"),
) -> None:
    """Search symbols by name."""
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

    for r in rows:
        shortf = _short_path(r["project_name"], r["file_path"], roots)
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        line = f"{r['project_name']}:{shortf}:{r['start_line'] or '-'} {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)


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
        line = f"{r['project_name']}:{shortf}:{lines} {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)


@app.command("index")
def index(project: str) -> None:
    """Index selected project."""
    config = ConfigManager()
    project_cfg = config.get_project(project)
    if project_cfg is None:
        raise typer.BadParameter(
            f"Project '{project}' not found.\n"
            f"Run: sampler project add {project} <absolute/path> --language python\n"
            "Then: sampler index {project}\n"
            "Use 'sampler project list' to see registered projects."
        )

    builder = IndexBuilder(db=_database())
    stats = builder.index_project(
        project_name=project_cfg.name,
        project_path=project_cfg.path,
        language=project_cfg.language,
    )
    console.print(
        "Indexed project "
        f"[bold]{stats['project']}[/bold]: discovered={stats['discovered']} indexed={stats['indexed']} "
        f"skipped={stats['skipped']} failed={stats['failed']}"
    )


@app.command("overview")
def overview(filepath: str) -> None:
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

    for r in rows:
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        lines = _format_line_range(r["start_line"], r["end_line"])
        line = f"{lines}: {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)


def _format_symbol_line(r: dict, roots: dict[str, Path]) -> str:
    shortf = _short_path(r["project_name"], r["file_path"], roots)
    name = r["qualified_name"] or r["name"]
    lines = _format_line_range(r["start_line"], r["end_line"])
    return f"{r['project_name']}:{shortf}:{lines} {r['type']} {name}"


def _resolve_or_report(matches: list[dict], symbol: str, roots: dict[str, Path]) -> bool:
    """Print an error/disambiguation message when matches != 1. Returns True if safe to proceed."""
    if len(matches) == 0:
        console.print(f"No symbol found matching '{symbol}'.")
        console.print("Tip: use 'sampler search <name> --project <project>' to find the right name.")
        return False
    if len(matches) > 1:
        console.print(f"Ambiguous symbol '{symbol}', found {len(matches)} matches:")
        for m in matches:
            console.print(f"  {_format_symbol_line(m, roots)}")
        console.print("Tip: narrow down with --project <project>.")
        return False
    return True


@app.command("callers")
def callers(
    symbol: str,
    project: str | None = typer.Option(None, "--project", "-p"),
) -> None:
    """Show symbols that CALL the given symbol."""
    engine = QueryEngine(db=_database())
    matches, rows = engine.callers(symbol, project)
    roots = _get_project_roots()
    if not _resolve_or_report(matches, symbol, roots):
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
) -> None:
    """Show symbols that reference the given symbol (any relationship type, broader than callers)."""
    engine = QueryEngine(db=_database())
    matches, rows = engine.usages(symbol, project)
    roots = _get_project_roots()
    if not _resolve_or_report(matches, symbol, roots):
        return
    if not rows:
        console.print(f"No usages found for {symbol}.")
        return
    for r in rows:
        console.print(f"{_format_symbol_line(r, roots)}  [{r['relation_type']}]")


@app.command("related")
def related(
    symbol: str,
    project: str | None = typer.Option(None, "--project", "-p"),
) -> None:
    """Show symbols related via CONTAINS (parent class / child methods)."""
    engine = QueryEngine(db=_database())
    matches, rows = engine.related(symbol, project)
    roots = _get_project_roots()
    if not _resolve_or_report(matches, symbol, roots):
        return
    if not rows:
        console.print(f"No related symbols found for {symbol}.")
        return
    for r in rows:
        console.print(f"{_format_symbol_line(r, roots)}  [{r['relation']}]")


if __name__ == "__main__":
    app()
