from __future__ import annotations

import hashlib
from pathlib import Path

from sampler.db import Database
from sampler.indexer.discover import discover_files
from sampler.indexer.parsers.go import GoParser
from sampler.indexer.parsers.python import PythonParser
from sampler.indexer.parsers.typescript import TypeScriptParser
from sampler.indexer.store import SymbolStore


class IndexBuilder:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.store = SymbolStore(db)
        self.parsers = {
            "python": PythonParser(),
            "go": GoParser(),
            "typescript": TypeScriptParser(),
            "javascript": TypeScriptParser(),
        }

    def index_project(self, project_name: str, project_path: str, language: str, force: bool = False) -> dict:
        parser = self.parsers.get(language)
        if parser is None:
            raise ValueError(f"Unsupported language: {language}")

        project_abs_path = str(Path(project_path).expanduser().resolve())
        project_id = self.db.add_project(name=project_name, path=project_abs_path, language=language)

        files = discover_files(project_path=project_abs_path, language=language)
        indexed = 0
        skipped = 0
        failed = 0

        for filepath in files:
            try:
                content = Path(filepath).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                failed += 1
                continue

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            previous = self.db.get_file(project_id=project_id, path=filepath)
            if not force and previous is not None and previous["hash"] == file_hash:
                skipped += 1
                continue

            symbols, relationships = parser.parse(content=content, filepath=filepath)
            self.store.save_symbols(
                project_id=project_id,
                filepath=filepath,
                language=language,
                file_hash=file_hash,
                symbols=symbols,
                relationships=relationships,
            )
            indexed += 1

        self.db.update_project_file_count(project_id)
        return {
            "project": project_name,
            "language": language,
            "discovered": len(files),
            "indexed": indexed,
            "skipped": skipped,
            "failed": failed,
        }
