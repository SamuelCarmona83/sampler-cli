from sampler.indexer.parsers.base import BaseParser


class GoParser(BaseParser):
    language = "go"

    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        _ = content, filepath
        return [], []
