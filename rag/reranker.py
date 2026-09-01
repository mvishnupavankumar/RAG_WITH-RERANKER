from __future__ import annotations

from functools import lru_cache
from typing import Any

from sentence_transformers import CrossEncoder

from config import RERANKER_BATCH_SIZE, RERANKER_MODEL


@lru_cache(maxsize=1)
def _model() -> CrossEncoder:
    return CrossEncoder(RERANKER_MODEL)


def rerank(
    query: str,
    documents: list[Any],
) -> list[tuple[Any, float]]:
    """Score query-document pairs with a dedicated cross-encoder reranker."""
    if not documents:
        return []

    pairs = [(query, document.page_content) for document in documents]
    scores = _model().predict(
        pairs,
        batch_size=RERANKER_BATCH_SIZE,
        show_progress_bar=False,
    )

    ranked = list(zip(documents, [float(score) for score in scores], strict=True))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
