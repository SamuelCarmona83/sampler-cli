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

    def resolve_symbol(self, name: str, project_name: str | None = None) -> list[dict]:
        """Find symbols matching a name/qualified_name. May return 0, 1, or many (ambiguous) matches."""
        rows = self.db.find_symbols(symbol_name=name, project_name=project_name)
        return [dict(row) for row in rows]

    def callers(self, name: str, project_name: str | None = None) -> tuple[list[dict], list[dict]]:
        """Returns (candidate matches, callers). Callers is only populated when exactly one match is found."""
        matches = self.resolve_symbol(name, project_name)
        if len(matches) != 1:
            return matches, []
        rows = self.db.get_callers(matches[0]["id"])
        return matches, [dict(row) for row in rows]

    def usages(self, name: str, project_name: str | None = None) -> tuple[list[dict], list[dict]]:
        """Returns (candidate matches, usages). Usages is only populated when exactly one match is found."""
        matches = self.resolve_symbol(name, project_name)
        if len(matches) != 1:
            return matches, []
        rows = self.db.get_usages(matches[0]["id"])
        return matches, [dict(row) for row in rows]

    def related(self, name: str, project_name: str | None = None) -> tuple[list[dict], list[dict]]:
        """Returns (candidate matches, related). Related is only populated when exactly one match is found."""
        matches = self.resolve_symbol(name, project_name)
        if len(matches) != 1:
            return matches, []
        rows = self.db.get_related(matches[0]["id"])
        return matches, [dict(row) for row in rows]
