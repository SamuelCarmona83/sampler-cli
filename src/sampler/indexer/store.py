from sampler.db import Database


class SymbolStore:
    def __init__(self, db: Database) -> None:
        self.db = db

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
        for symbol in symbols:
            inserted_id = self.db.insert_symbol(file_id=file_id, symbol=symbol)
            qualified = symbol.get("qualified_name") or symbol.get("name")
            if qualified:
                symbol_id_map[qualified] = inserted_id
            name = symbol.get("name")
            if name and name not in symbol_id_map:
                symbol_id_map[name] = inserted_id

        for relation in relationships:
            source_key = relation.get("source")
            target_key = relation.get("target")
            if not source_key or not target_key:
                continue

            source_id = symbol_id_map.get(source_key)
            if source_id is None:
                source_id = self.db.find_symbol_id_in_project(project_id=project_id, symbol_name=source_key)

            target_id = symbol_id_map.get(target_key)
            if target_id is None:
                target_id = self.db.find_symbol_id_in_project(project_id=project_id, symbol_name=target_key)

            if source_id is None or target_id is None:
                continue

            self.db.insert_relationship(source_id=source_id, target_id=target_id, relation=relation)
