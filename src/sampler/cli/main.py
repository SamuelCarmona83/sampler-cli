from pathlib import Path

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

    table = Table(title="Projects")
    table.add_column("Name")
    table.add_column("Path")
    table.add_column("Language")
    table.add_column("Enabled")

    for project in projects:
        table.add_row(
            project.name,
            project.path,
            project.language,
            "yes" if project.enabled else "no",
        )

    console.print(table)


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

    table = Table(title=f"Search results: {query}")
    table.add_column("Project")
    table.add_column("File")
    table.add_column("Type")
    table.add_column("Name")
    table.add_column("Line")

    for row in rows:
        table.add_row(
            str(row["project_name"]),
            str(row["file_path"]),
            str(row["type"]),
            str(row["qualified_name"] or row["name"]),
            str(row["start_line"] or "-"),
        )

    console.print(table)
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
def overview(filepath: str) -> None:
    """Show symbols for file."""
    engine = QueryEngine(db=_database())
    rows = engine.overview(filepath=filepath)

    table = Table(title=f"Overview: {filepath}")
    table.add_column("Project")
    table.add_column("Type")
    table.add_column("Name")
    table.add_column("Line")

    for row in rows:
        table.add_row(
            str(row["project_name"]),
            str(row["type"]),
            str(row["qualified_name"] or row["name"]),
            str(row["start_line"] or "-"),
        )

    console.print(table)
    console.print(f"Found {len(rows)} symbol(s)")


if __name__ == "__main__":
    app()
