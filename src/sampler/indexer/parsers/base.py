from abc import ABC, abstractmethod


class BaseParser(ABC):
    language: str

    @abstractmethod
    def parse(self, content: str, filepath: str) -> tuple[list[dict], list[dict]]:
        raise NotImplementedError
