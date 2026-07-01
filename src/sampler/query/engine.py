from __future__ import annotations

from sampler.db import Database


class QueryEngine:
    def __init__(self, db: Database) -> None:
        self.db = db

    def search(self, query: str, project_name: str | None = None, types: list[str] | None = None, limit: int | None = None, offset: int = 0) -> list[dict]:
        rows = self.db.search_symbols(query=query, project_name=project_name, types=types, limit=limit, offset=offset)
        return [dict(row) for row in rows]

    def overview(self, filepath: str, project_name: str | None = None) -> list[dict]:
        rows = self.db.get_symbols_by_filepath(filepath=filepath, project_name=project_name)
        return [dict(row) for row in rows]

    def list_symbols(self, project_name: str, types: list[str] | None = None, limit: int | None = None, offset: int = 0) -> list[dict]:
        rows = self.db.list_symbols(project_name=project_name, types=types, limit=limit, offset=offset)
        return [dict(row) for row in rows]
