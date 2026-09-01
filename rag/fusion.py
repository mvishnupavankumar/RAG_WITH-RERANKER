from __future__ import annotations

from typing import Any


def document_key(doc: Any) -> str:
    """Stable key for identifying the same chunk across retrievers."""
    metadata = doc.metadata
    source_id = metadata.get("source_id", "")
    chunk_id = metadata.get("chunk_id", "")
    return f"{source_id}:{chunk_id}"


def reciprocal_rank_fusion(
    dense_results: list[tuple[Any, float]],
    sparse_results: list[tuple[Any, float]],
    rrf_k: int = 60,
) -> list[tuple[Any, float]]:
    """Fuse ranked retrieval results using Reciprocal Rank Fusion (RRF).

    RRF combines rank positions rather than raw retrieval scores, so the
    different score scales of FAISS and BM25 do not need normalization.
    """
    if rrf_k <= 0:
        raise ValueError("rrf_k must be greater than zero")

    documents_by_key: dict[str, Any] = {}
    fused_scores: dict[str, float] = {}

    for rank, (doc, _score) in enumerate(dense_results, start=1):
        key = document_key(doc)
        documents_by_key[key] = doc
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (rrf_k + rank)

    for rank, (doc, _score) in enumerate(sparse_results, start=1):
        key = document_key(doc)
        documents_by_key[key] = doc
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (rrf_k + rank)

    ranked = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    return [(documents_by_key[key], score) for key, score in ranked]
