from sampler.db import Database


class SymbolStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def _dedupe_candidates(rows: list[dict]) -> list[dict]:
        uniq: dict[tuple, dict] = {}
        for row in rows:
            key = (
                row.get("file_path"),
                row.get("qualified_name") or row.get("name"),
                row.get("type"),
                row.get("start_line"),
                row.get("end_line"),
            )
            uniq.setdefault(key, row)
        return list(uniq.values())

    def _resolve_relation_symbol_id(
        self,
        project_id: int,
        key: str,
        *,
        source_key: str,
        relation_type: str,
        local_exact: dict[str, int],
        local_by_name: dict[str, list[int]],
    ) -> int | None:
        # 1) Exact local match (same file batch) remains the strongest signal.
        direct = local_exact.get(key)
        if direct is not None:
            return direct

        # 2) Exact project-wide lookup.
        exact = self.db.find_symbol_id_in_project(project_id=project_id, symbol_name=key)
        if exact is not None:
            return exact

        leaf = key.split(".")[-1]

        # 3) Fast local leaf lookup, only if unique (avoid false positives).
        local_leaf = local_by_name.get(leaf, [])
        if len(local_leaf) == 1:
            return local_leaf[0]

        # 4) Class-aware heuristic: `self.method` from `Class.fn` should prefer `Class.method`.
        if relation_type == "CALLS" and "." in source_key:
            source_class = source_key.split(".", 1)[0]
            class_target = f"{source_class}.{leaf}"
            class_exact = local_exact.get(class_target)
            if class_exact is not None:
                return class_exact
            class_exact_db = self.db.find_symbol_id_in_project(project_id=project_id, symbol_name=class_target)
            if class_exact_db is not None:
                return class_exact_db

        # 5) Project candidates by leaf/suffix; resolve only when confidently unique.
        candidates = [dict(r) for r in self.db.find_symbol_candidates_in_project(project_id, key)]
        candidates = self._dedupe_candidates(candidates)

        if len(candidates) == 1:
            return int(candidates[0]["id"])

        if candidates and "." in key:
            prefix_hint = key.rsplit(".", 1)[0].split(".")[-1].lower()
            hinted = [
                c
                for c in candidates
                if prefix_hint in ((c.get("qualified_name") or "").lower())
                or prefix_hint in ((c.get("file_path") or "").lower())
            ]
            hinted = self._dedupe_candidates(hinted)
            if len(hinted) == 1:
                return int(hinted[0]["id"])

        # Ambiguous or unresolved: skip relation to preserve precision.
        return None

    def save_symbols(
        self,
        project_id: int,
        filepath: str,
        language: str,
        file_hash: str,
        symbols: list[dict],
        relationships: list[dict],
    ) -> None:
        file_id = self.db.upsert_file(project_id=project_id, path=filepath, language=language, file_hash=file_hash)
        self.db.clear_file_data(file_id)

        symbol_id_map: dict[str, int] = {}
        local_by_name: dict[str, list[int]] = {}
        for symbol in symbols:
            inserted_id = self.db.insert_symbol(file_id=file_id, symbol=symbol)
            qualified = symbol.get("qualified_name") or symbol.get("name")
            if qualified:
                symbol_id_map[qualified] = inserted_id
            name = symbol.get("name")
            if name:
                local_by_name.setdefault(name, []).append(inserted_id)
                if name not in symbol_id_map:
                    symbol_id_map[name] = inserted_id

        for relation in relationships:
            source_key = relation.get("source")
            target_key = relation.get("target")
            if not source_key or not target_key:
                continue

            source_id = self._resolve_relation_symbol_id(
                project_id,
                source_key,
                source_key=source_key,
                relation_type=relation.get("type") or "",
                local_exact=symbol_id_map,
                local_by_name=local_by_name,
            )
            target_id = self._resolve_relation_symbol_id(
                project_id,
                target_key,
                source_key=source_key,
                relation_type=relation.get("type") or "",
                local_exact=symbol_id_map,
                local_by_name=local_by_name,
            )

            if source_id is None or target_id is None:
                continue

            self.db.insert_relationship(source_id=source_id, target_id=target_id, relation=relation)
