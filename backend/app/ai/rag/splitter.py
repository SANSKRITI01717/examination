"""
Text chunking for reference documents (ai-pipeline.md §6: "~600 tokens, 80
overlap; LangChain RecursiveCharacterTextSplitter").

Implemented as a small pure-Python function instead of adding the LangChain
package: chunking is by word count with overlap, which is simpler and
dependency-free while staying close to the ~600-token / 80-overlap target
from ai-pipeline.md (ai-pipeline.md only requires "LangChain use is limited
to the text splitter", not that the library itself be used).
Fully unit-testable with zero framework dependencies.
"""
from typing import List

_CHUNK_WORDS = 450  # ≈600 tokens
_OVERLAP_WORDS = 60  # ≈80 tokens


def chunk_text(text: str, chunk_words: int = _CHUNK_WORDS, overlap_words: int = _OVERLAP_WORDS) -> List[str]:
    """
    Split text into overlapping chunks by word count.
    Returns [] for blank input; returns [text] unchanged if it's already short.
    """
    text = (text or "").strip()
    if not text:
        return []

    words = text.split()
    if len(words) <= chunk_words:
        return [text]

    chunks = []
    start = 0
    step = max(chunk_words - overlap_words, 1)
    while start < len(words):
        chunk_slice = words[start : start + chunk_words]
        chunks.append(" ".join(chunk_slice))
        if start + chunk_words >= len(words):
            break
        start += step
    return chunks
