"""Vector store for historical fault case retrieval.

Uses chromadb if available, otherwise falls back to a simple
keyword-based in-memory mock that preserves the same interface.
"""

from __future__ import annotations

import logging
from typing import Any

from utils.mock_data import HISTORICAL_CASES

logger = logging.getLogger("fault_agent")

_HAS_CHROMA = False
_chroma_client = None
_chroma_collection = None

try:
    import chromadb
    _HAS_CHROMA = True
    logger.info("chromadb available, using real vector store")
except ImportError:
    logger.info("chromadb not available, using in-memory mock vector store")


def _init_chroma() -> None:
    """Initialize chromadb client and collection, seed with historical cases."""
    global _chroma_client, _chroma_collection
    if _chroma_client is not None:
        return
    _chroma_client = chromadb.Client()  # in-memory mode
    _chroma_collection = _chroma_client.get_or_create_collection(
        name="fault_cases",
        metadata={"hnsw:space": "cosine"},
    )
    for i, case in enumerate(HISTORICAL_CASES):
        doc_text = f"{case['title']} {case['root_cause']} {' '.join(case['symptoms'])}"
        _chroma_collection.add(
            ids=[case["case_id"]],
            documents=[doc_text],
            metadatas=[{"resolution": case["resolution"]}],
        )


class VectorStore:
    """Unified interface for fault case retrieval."""

    def __init__(self) -> None:
        if _HAS_CHROMA:
            _init_chroma()

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search for similar historical fault cases.

        Args:
            query: Fault feature description to match against.
            top_k: Number of results to return.

        Returns:
            List of case dicts with case_id, title, symptoms, root_cause, resolution.
        """
        if _HAS_CHROMA and _chroma_collection is not None:
            results = _chroma_collection.query(
                query_texts=[query],
                n_results=top_k,
            )
            cases = []
            for i, doc_id in enumerate(results["ids"][0]):
                case = next(c for c in HISTORICAL_CASES if c["case_id"] == doc_id)
                cases.append(case)
            return cases

        # Mock: simple keyword matching with scoring
        scored: list[tuple[float, dict]] = []
        query_words = set(query.lower().split())
        for case in HISTORICAL_CASES:
            searchable = f"{case['title']} {case['root_cause']} {' '.join(case['symptoms'])}".lower()
            searchable_words = set(searchable.split())
            overlap = len(query_words & searchable_words)
            score = overlap / max(len(query_words), 1)
            scored.append((score, case))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [case for _, case in scored[:top_k]]