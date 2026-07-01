import sqlite3
import json
from pathlib import Path


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT NOT NULL,
                    language TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER REFERENCES projects(id),
                    path TEXT NOT NULL,
                    language TEXT,
                    hash TEXT,
                    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, path)
                );

                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER REFERENCES files(id),
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    qualified_name TEXT,
                    signature TEXT,
                    docstring TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    metadata JSON
                );

                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER REFERENCES symbols(id),
                    target_id INTEGER REFERENCES symbols(id),
                    type TEXT NOT NULL,
                    line INTEGER,
                    metadata JSON
                );

                CREATE TABLE IF NOT EXISTS project_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_project_id INTEGER REFERENCES projects(id),
                    target_project_id INTEGER REFERENCES projects(id),
                    type TEXT NOT NULL,
                    metadata JSON,
                    UNIQUE(source_project_id, target_project_id, type)
                );

                CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
                CREATE INDEX IF NOT EXISTS idx_symbols_qualified ON symbols(qualified_name);
                CREATE INDEX IF NOT EXISTS idx_relations_source ON relationships(source_id);
                CREATE INDEX IF NOT EXISTS idx_relations_target ON relationships(target_id);
                CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id);
                """
            )
            conn.commit()

    def add_project(self, name: str, path: str, language: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO projects(name, path, language)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    path=excluded.path,
                    language=excluded.language,
                    indexed_at=CURRENT_TIMESTAMP
                """,
                (name, path, language),
            )
            conn.commit()

            if cur.lastrowid:
                return int(cur.lastrowid)

            row = conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise RuntimeError("Failed to upsert project")
            return int(row["id"])

    def list_projects(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, path, language, indexed_at, file_count
                FROM projects
                ORDER BY name
                """
            ).fetchall()
            return rows

    def get_project(self, name: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, name, path, language, indexed_at, file_count FROM projects WHERE name = ?",
                (name,),
            ).fetchone()

    def remove_project(self, name: str) -> None:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
            if row is None:
                return
            project_id = int(row["id"])
            conn.execute(
                "DELETE FROM relationships WHERE source_id IN (SELECT id FROM symbols WHERE file_id IN (SELECT id FROM files WHERE project_id = ?))",
                (project_id,),
            )
            conn.execute(
                "DELETE FROM relationships WHERE target_id IN (SELECT id FROM symbols WHERE file_id IN (SELECT id FROM files WHERE project_id = ?))",
                (project_id,),
            )
            conn.execute(
                "DELETE FROM symbols WHERE file_id IN (SELECT id FROM files WHERE project_id = ?)",
                (project_id,),
            )
            conn.execute("DELETE FROM files WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM project_dependencies WHERE source_project_id = ? OR target_project_id = ?", (project_id, project_id))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

    def get_file(self, project_id: int, path: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, project_id, path, language, hash, last_indexed FROM files WHERE project_id = ? AND path = ?",
                (project_id, path),
            ).fetchone()

    def upsert_file(self, project_id: int, path: str, language: str, file_hash: str) -> int:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO files(project_id, path, language, hash)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, path) DO UPDATE SET
                    language=excluded.language,
                    hash=excluded.hash,
                    last_indexed=CURRENT_TIMESTAMP
                """,
                (project_id, path, language, file_hash),
            )
            row = conn.execute(
                "SELECT id FROM files WHERE project_id = ? AND path = ?",
                (project_id, path),
            ).fetchone()
            conn.commit()
            if row is None:
                raise RuntimeError("Failed to upsert file")
            return int(row["id"])

    def clear_file_data(self, file_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM relationships WHERE source_id IN (SELECT id FROM symbols WHERE file_id = ?)",
                (file_id,),
            )
            conn.execute(
                "DELETE FROM relationships WHERE target_id IN (SELECT id FROM symbols WHERE file_id = ?)",
                (file_id,),
            )
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            conn.commit()

    def insert_symbol(self, file_id: int, symbol: dict) -> int:
        with self.connect() as conn:
            metadata = symbol.get("metadata")
            row = conn.execute(
                """
                INSERT INTO symbols(
                    file_id, type, name, qualified_name, signature,
                    docstring, start_line, end_line, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_id,
                    symbol.get("type"),
                    symbol.get("name"),
                    symbol.get("qualified_name"),
                    symbol.get("signature"),
                    symbol.get("docstring"),
                    symbol.get("start_line"),
                    symbol.get("end_line"),
                    json.dumps(metadata) if metadata is not None else None,
                ),
            )
            conn.commit()
            return int(row.lastrowid)

    def find_symbol_id_in_project(self, project_id: int, symbol_name: str) -> int | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT s.id
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE f.project_id = ?
                  AND (s.qualified_name = ? OR s.name = ?)
                ORDER BY s.id ASC
                LIMIT 1
                """,
                (project_id, symbol_name, symbol_name),
            ).fetchone()
            return None if row is None else int(row["id"])

    def insert_relationship(self, source_id: int, target_id: int, relation: dict) -> None:
        with self.connect() as conn:
            metadata = relation.get("metadata")
            conn.execute(
                """
                INSERT INTO relationships(source_id, target_id, type, line, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    target_id,
                    relation.get("type"),
                    relation.get("line"),
                    json.dumps(metadata) if metadata is not None else None,
                ),
            )
            conn.commit()

    def update_project_file_count(self, project_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET file_count = (SELECT COUNT(*) FROM files WHERE project_id = ?),
                    indexed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (project_id, project_id),
            )
            conn.commit()

    def search_symbols(self, query: str, project_name: str | None = None, types: list[str] | None = None, limit: int | None = None, offset: int = 0) -> list[sqlite3.Row]:
        where = "WHERE (lower(s.name) LIKE lower(?) OR lower(COALESCE(s.qualified_name, '')) LIKE lower(?))"
        params: list = [f"%{query}%", f"%{query}%"]
        if project_name:
            where += " AND p.name = ?"
            params.append(project_name)
        if types:
            ph = ",".join("?" * len(types))
            where += f" AND s.type IN ({ph})"
            params.extend(types)

        sql = f"""
                SELECT
                    s.type,
                    s.name,
                    s.qualified_name,
                    s.signature,
                    s.start_line,
                    f.path AS file_path,
                    p.name AS project_name
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                JOIN projects p ON f.project_id = p.id
                {where}
                ORDER BY p.name, f.path, s.start_line
                """
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def get_symbols_by_filepath(self, filepath: str, project_name: str | None = None) -> list[sqlite3.Row]:
        where = "WHERE f.path = ?"
        params: list[str] = [filepath]
        if project_name:
            where += " AND p.name = ?"
            params.append(project_name)

        with self.connect() as conn:
            return conn.execute(
                f"""
                SELECT
                    s.type,
                    s.name,
                    s.qualified_name,
                    s.signature,
                    s.start_line,
                    f.path AS file_path,
                    p.name AS project_name
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                JOIN projects p ON f.project_id = p.id
                {where}
                ORDER BY s.start_line
                """,
                params,
            ).fetchall()

    def list_symbols(self, project_name: str, types: list[str] | None = None, limit: int | None = None, offset: int = 0) -> list[sqlite3.Row]:
        where = "WHERE p.name = ?"
        params: list = [project_name]
        if types:
            ph = ",".join("?" * len(types))
            where += f" AND s.type IN ({ph})"
            params.extend(types)

        sql = f"""
                SELECT
                    s.type,
                    s.name,
                    s.qualified_name,
                    s.signature,
                    s.start_line,
                    f.path AS file_path,
                    p.name AS project_name
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                JOIN projects p ON f.project_id = p.id
                {where}
                ORDER BY f.path, s.start_line
                """
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()
