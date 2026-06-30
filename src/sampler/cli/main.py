from pathlib import Path
import json

import typer
from rich.console import Console
from rich.table import Table

from sampler import __version__
from sampler.config import ConfigManager
from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.query.engine import QueryEngine

app = typer.Typer(help="Sampler CLI")
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
        console.print(f"{project.name} {disp} {project.language}")


@project_app.command("add")
def project_add(name: str, path: str, language: str = "python") -> None:
    """Register project in global config."""
    config = ConfigManager()
    try:
        project = config.add_project(name=name, path=path, language=language)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
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


@app.command("search")
def search(
    query: str,
    project: str | None = typer.Option(None, "--project", "-p", help="Limit to project"),
    format: str = typer.Option(
        "compact", "--format", "-f", help="Output format: compact (default, token-efficient), table, json"
    ),
) -> None:
    """Search symbols by name. Use --format compact|json for minimal tokens when feeding LLMs."""
    engine = QueryEngine(db=_database())
    rows = engine.search(query=query, project_name=project)
    roots = _get_project_roots()

    if format == "json":
        lean = []
        for r in rows:
            lean.append(
                {
                    "project": r["project_name"],
                    "file": _short_path(r["project_name"], r["file_path"], roots),
                    "type": r["type"],
                    "name": r["qualified_name"] or r["name"],
                    "line": r["start_line"],
                    "signature": r.get("signature"),
                }
            )
        # minified for lowest token count
        console.print(json.dumps(lean, separators=(",", ":")))
        return

    if format == "table":
        title = f"Search results: {query}"
        if project:
            table = Table(title=title)
            table.add_column("File")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Line")
            for r in rows:
                shortf = _short_path(r["project_name"], r["file_path"], roots)
                name = r["qualified_name"] or r["name"]
                table.add_row(
                    shortf,
                    str(r["type"]),
                    str(name),
                    str(r["start_line"] or "-"),
                )
        else:
            table = Table(title=title)
            table.add_column("Project")
            table.add_column("File")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Line")
            for r in rows:
                shortf = _short_path(r["project_name"], r["file_path"], roots)
                name = r["qualified_name"] or r["name"]
                table.add_row(
                    str(r["project_name"]),
                    shortf,
                    str(r["type"]),
                    str(name),
                    str(r["start_line"] or "-"),
                )
        console.print(table)
        console.print(f"Found {len(rows)} result(s)")
        return

    # default: compact (token-efficient, LLM friendly, no borders/repeats)
    for r in rows:
        shortf = _short_path(r["project_name"], r["file_path"], roots)
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        line = f"{r['project_name']}:{shortf}:{r['start_line'] or '-'} {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)
    console.print(f"Found {len(rows)} result(s)")


@app.command("index")
def index(project: str) -> None:
    """Index selected project."""
    config = ConfigManager()
    project_cfg = config.get_project(project)
    if project_cfg is None:
        raise typer.BadParameter(f"Project '{project}' not found. Use 'sampler project list'.")

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
def overview(
    filepath: str,
    format: str = typer.Option(
        "compact", "--format", "-f", help="Output format: compact (default, token-efficient), table, json"
    ),
) -> None:
    """Show symbols for file. Use --format compact|json for minimal tokens when feeding LLMs."""
    engine = QueryEngine(db=_database())
    rows = engine.overview(filepath=filepath)
    roots = _get_project_roots()

    # For overview the input filepath is known; compute a short display version once
    # (we don't know project for sure, so use best-effort short from any root or tail)
    disp_path = filepath
    for root in roots.values():
        try:
            disp_path = str(Path(filepath).resolve().relative_to(root))
            break
        except Exception:
            continue
    if disp_path == filepath:
        p = Path(filepath)
        disp_path = "/".join(p.parts[-2:]) if len(p.parts) >= 3 else p.name

    if format == "json":
        lean = []
        for r in rows:
            lean.append(
                {
                    "project": r["project_name"],
                    "file": disp_path,
                    "type": r["type"],
                    "name": r["qualified_name"] or r["name"],
                    "line": r["start_line"],
                    "signature": r.get("signature"),
                }
            )
        console.print(json.dumps(lean, separators=(",", ":")))
        return

    if format == "table":
        table = Table(title=f"Overview: {disp_path}")
        table.add_column("Project")
        table.add_column("Type")
        table.add_column("Name")
        table.add_column("Line")
        for r in rows:
            name = r["qualified_name"] or r["name"]
            table.add_row(
                str(r["project_name"]),
                str(r["type"]),
                str(name),
                str(r["start_line"] or "-"),
            )
        console.print(table)
        console.print(f"Found {len(rows)} symbol(s)")
        return

    # default: compact (ultra lean for file-focused view: no repeated file path)
    for r in rows:
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        line = f"{r['start_line'] or '-'}: {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)
    console.print(f"Found {len(rows)} symbol(s)")


if __name__ == "__main__":
    app()
