from sampler.indexer.parsers.base import BaseParser


class TypeScriptParser(BaseParser):
    language = "typescript"

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        _ = content, filepath
        return [], []
