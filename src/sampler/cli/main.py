from pathlib import Path

import typer
from rich.console import Console

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
        console.print(f"{project.name} {disp}")


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
def search(query: str, project: str | None = None) -> None:
    """Search symbols by name."""
    engine = QueryEngine(db=_database())
    rows = engine.search(query=query, project_name=project)
    roots = _get_project_roots()

    for r in rows:
        shortf = _short_path(r["project_name"], r["file_path"], roots)
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        line = f"{r['project_name']}:{shortf}:{r['start_line'] or '-'} {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)


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
def overview(filepath: str) -> None:
    """Show symbols for file."""
    engine = QueryEngine(db=_database())
    rows = engine.overview(filepath=filepath)

    for r in rows:
        name = r["qualified_name"] or r["name"]
        sig = r.get("signature") or ""
        line = f"{r['start_line'] or '-'}: {r['type']} {name}"
        if sig:
            line += f"  {sig}"
        console.print(line)


if __name__ == "__main__":
    app()
