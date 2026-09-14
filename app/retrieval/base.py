from dataclasses import dataclass
from typing import List, Protocol

from .chunker import Chunk


@dataclass
class Hit:
    chunk: Chunk
    score: float


class Retriever(Protocol):
    def build(self, chunks: List[Chunk]) -> None: ...
    def search(self, query: str, k: int = 4) -> List[Hit]: ...
