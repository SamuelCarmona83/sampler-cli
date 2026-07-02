from __future__ import annotations

from pathlib import Path

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

    def relationships_among(self, rows: list[dict]) -> list[dict]:
        """Relationships where both endpoints are within the given rows (for the 'bars' output style)."""
        ids = [r["id"] for r in rows if r.get("id") is not None]
        return [dict(row) for row in self.db.get_relationships_among(ids)]

    def resolve_symbol(
        self,
        name: str,
        project_name: str | None = None,
        file_path: str | None = None,
    ) -> list[dict]:
        """Find symbols matching a name/qualified_name. May return 0, 1, or many (ambiguous) matches."""
        rows = self.db.find_symbols(symbol_name=name, project_name=project_name, file_path=file_path)
        # Guard against duplicate logical symbols (e.g. stale duplicate rows after re-index cycles).
        uniq: dict[tuple, dict] = {}
        for row in rows:
            item = dict(row)
            key = (
                item.get("project_name"),
                item.get("file_path"),
                item.get("qualified_name") or item.get("name"),
                item.get("type"),
                item.get("start_line"),
                item.get("end_line"),
            )
            uniq.setdefault(key, item)
        return list(uniq.values())

    @staticmethod
    def _collapse_duplicate_match_rows(matches: list[dict]) -> list[dict]:
        """Collapse repeated logical symbol rows that differ only by id/storage duplication."""
        if len(matches) <= 1:
            return matches
        first = matches[0]
        sig0 = (
            first.get("project_name"),
            first.get("file_path"),
            first.get("qualified_name") or first.get("name"),
            first.get("type"),
            first.get("start_line"),
            first.get("end_line"),
        )
        for m in matches[1:]:
            sig = (
                m.get("project_name"),
                m.get("file_path"),
                m.get("qualified_name") or m.get("name"),
                m.get("type"),
                m.get("start_line"),
                m.get("end_line"),
            )
            if sig != sig0:
                return matches
        return [first]

    def callers(
        self,
        name: str,
        project_name: str | None = None,
        file_path: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Returns (candidate matches, callers). Callers is only populated when exactly one match is found."""
        matches = self._collapse_duplicate_match_rows(self.resolve_symbol(name, project_name, file_path))
        if len(matches) != 1:
            return matches, []
        rows = self.db.get_callers(matches[0]["id"])
        return matches, [dict(row) for row in rows]

    def usages(
        self,
        name: str,
        project_name: str | None = None,
        file_path: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Returns (candidate matches, usages). Usages is only populated when exactly one match is found."""
        matches = self._collapse_duplicate_match_rows(self.resolve_symbol(name, project_name, file_path))
        if len(matches) != 1:
            return matches, []
        rows = self.db.get_usages(matches[0]["id"])
        return matches, [dict(row) for row in rows]

    def related(
        self,
        name: str,
        project_name: str | None = None,
        file_path: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """Returns (candidate matches, related). Related is only populated when exactly one match is found."""
        matches = self._collapse_duplicate_match_rows(self.resolve_symbol(name, project_name, file_path))
        if len(matches) != 1:
            return matches, []
        rows = self.db.get_related(matches[0]["id"])
        return matches, [dict(row) for row in rows]

    @staticmethod
    def _is_test_path(path: str) -> bool:
        p = path.replace("\\", "/").lower()
        name = Path(path).name.lower()
        return "/tests/" in p or name.startswith("test_") or name.endswith("_test.py")

    def stale_code_candidates(self, project_name: str) -> list[dict]:
        """Detect code likely stale: function/method called by tests but not by non-test code."""
        edges = [dict(r) for r in self.db.get_project_call_edges(project_name)]
        by_target: dict[int, dict] = {}

        function_types = {"function", "async function", "method", "async method"}
        for edge in edges:
            if edge["target_type"] not in function_types:
                continue

            target_id = int(edge["target_id"])
            entry = by_target.setdefault(
                target_id,
                {
                    "id": target_id,
                    "type": edge["target_type"],
                    "name": edge["target_name"],
                    "qualified_name": edge["target_qualified_name"],
                    "start_line": edge["target_start_line"],
                    "end_line": edge["target_end_line"],
                    "file_path": edge["target_file_path"],
                    "project_name": project_name,
                    "test_callers": set(),
                    "non_test_callers": set(),
                },
            )

            caller_name = edge["source_qualified_name"] or edge["source_name"]
            if self._is_test_path(edge["source_file_path"]):
                entry["test_callers"].add(caller_name)
            else:
                entry["non_test_callers"].add(caller_name)

        stale: list[dict] = []
        for entry in by_target.values():
            if entry["test_callers"] and not entry["non_test_callers"]:
                stale.append(
                    {
                        **entry,
                        "test_callers": sorted(entry["test_callers"]),
                        "non_test_callers": sorted(entry["non_test_callers"]),
                        "test_caller_count": len(entry["test_callers"]),
                        "non_test_caller_count": len(entry["non_test_callers"]),
                    }
                )

        stale.sort(key=lambda r: (r["file_path"], r["start_line"], r["qualified_name"] or r["name"]))
        return stale
