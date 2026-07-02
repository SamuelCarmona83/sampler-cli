from __future__ import annotations

import hashlib
import re
from pathlib import Path

from typing import TYPE_CHECKING

from sampler.db import Database
from sampler.indexer.discover import discover_files, discover_files_multi
from sampler.indexer.imports import extract_imports
from sampler.indexer.parsers.go import GoParser
from sampler.indexer.parsers.python import PythonParser
from sampler.indexer.parsers.typescript import TypeScriptParser
from sampler.indexer.parsers.vue import VueParser
from sampler.indexer.store import SymbolStore
from sampler.viz.discover_emit import emit_discover
from sampler.viz.events import FileParsing, LogLine, Stage, StageChanged

if TYPE_CHECKING:
    from sampler.viz.bus import EventBus, NullEventBus


class IndexBuilder:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.store = SymbolStore(db)
        self.parsers = {
            "python": PythonParser(),
            "go": GoParser(),
            "typescript": TypeScriptParser(),
            "javascript": TypeScriptParser(),
            "vue": VueParser(),
        }

    def index_project(
        self,
        project_name: str,
        project_path: str,
        language: str,
        force: bool = False,
        event_bus: EventBus | NullEventBus | None = None,
    ) -> dict:
        is_auto = language.lower() == "auto"
        if not is_auto and language not in self.parsers:
            raise ValueError(f"Unsupported language: {language}")

        project_abs_path = str(Path(project_path).expanduser().resolve())
        project_id = self.db.add_project(name=project_name, path=project_abs_path, language=language)

        if is_auto:
            # Monorepo/multi-language mode: detect each file's language individually.
            file_entries = discover_files_multi(project_path=project_abs_path)
        else:
            file_entries = [(f, language) for f in discover_files(project_path=project_abs_path, language=language)]

        bus = event_bus
        if bus is not None:
            emit_discover(bus, project_abs_path, file_entries)
            bus.emit(StageChanged(Stage.PARSING))

        indexed = 0
        skipped = 0
        failed = 0
        all_imports: set[str] = set()
        total = len(file_entries)
        parse_idx = 0

        for filepath, file_language in file_entries:
            parser = self.parsers.get(file_language)
            if parser is None:
                failed += 1
                continue

            try:
                content = Path(filepath).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                failed += 1
                continue

            all_imports.update(extract_imports(content, file_language))

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            previous = self.db.get_file(project_id=project_id, path=filepath)
            if not force and previous is not None and previous["hash"] == file_hash:
                skipped += 1
                continue

            if bus is not None:
                bus.emit(FileParsing(path=filepath, index=parse_idx, total=total))
                bus.emit(LogLine(message=f"+ parser {Path(filepath).name}"))

            symbols, relationships = parser.parse(content=content, filepath=filepath)
            if bus is not None:
                bus.emit(StageChanged(Stage.RELATIONSHIPS))
            self.store.save_symbols(
                project_id=project_id,
                filepath=filepath,
                language=file_language,
                file_hash=file_hash,
                symbols=symbols,
                relationships=relationships,
                event_bus=bus,
            )
            indexed += 1
            parse_idx += 1

        self.db.update_project_file_count(project_id)
        self._resolve_project_dependencies(project_id, project_name, all_imports)
        return {
            "project": project_name,
            "language": language,
            "discovered": len(file_entries),
            "indexed": indexed,
            "skipped": skipped,
            "failed": failed,
        }

    def _resolve_project_dependencies(self, project_id: int, project_name: str, imports: set[str]) -> None:
        """Best-effort: match imported module/package strings against OTHER registered
        (and already-indexed) projects' names, and record CROSS-PROJECT `IMPORTS` edges.
        """
        self.db.clear_project_dependencies_from(project_id)
        if not imports:
            return

        other_projects = [p for p in self.db.list_projects() if p["name"] != project_name]
        for other in other_projects:
            if any(self._import_matches_project(imp, other["name"]) for imp in imports):
                self.db.insert_project_dependency(project_id, int(other["id"]), "IMPORTS")

    @staticmethod
    def _import_matches_project(import_path: str, project_name: str) -> bool:
        parts = [p for p in re.split(r"[./\\-]", import_path.strip()) if p]
        return project_name.lower() in (p.lower() for p in parts)
