from sampler.indexer.parsers.python import PythonParser


def test_python_parser_extracts_symbols_and_relationships() -> None:
    parser = PythonParser()
    code = """
import os

class UserService:
    def get_user(self, user_id: str):
        return format_user(user_id)

def format_user(user_id: str):
    return user_id
"""

    symbols, relationships = parser.parse(code, "/tmp/sample.py")

    symbol_names = {s["qualified_name"] for s in symbols}
    assert "UserService" in symbol_names
    assert "UserService.get_user" in symbol_names
    assert "format_user" in symbol_names

    rel_types = {(r["source"], r["target"], r["type"]) for r in relationships}
    assert ("UserService", "UserService.get_user", "CONTAINS") in rel_types
    assert ("UserService.get_user", "format_user", "CALLS") in rel_types
