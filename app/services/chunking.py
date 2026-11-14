import re
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str


def _chunk_settings(size: int | None, overlap: int | None) -> tuple[int, int]:
    settings = get_settings()
    chunk_size = settings.chunk_size if size is None else size
    chunk_overlap = settings.chunk_overlap if overlap is None else overlap
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk size must be positive and greater than a non-negative overlap")
    return chunk_size, chunk_overlap


def _windows(text: str, size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(Chunk(len(chunks), text[start:end]))
        if end == len(text):
            break
        start = end - overlap
    return chunks


def fixed_chunks(
    text: str,
    size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    chunk_size, chunk_overlap = _chunk_settings(size, overlap)
    return _windows(text, chunk_size, chunk_overlap)


def recursive_chunks(
    text: str,
    size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    chunk_size, chunk_overlap = _chunk_settings(size, overlap)
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundaries = [
                match.end()
                for match in re.finditer(r"\n\s*\n", text[start:end])
                if match.end() > chunk_size - chunk_overlap
            ]
            if boundaries:
                end = start + boundaries[-1]
        chunks.append(Chunk(len(chunks), text[start:end]))
        if end == len(text):
            break
        start = end - chunk_overlap
    return chunks


def make_chunks(text: str, strategy: str) -> list[Chunk]:
    if strategy == "fixed":
        return fixed_chunks(text)
    return recursive_chunks(text)
