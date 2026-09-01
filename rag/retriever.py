from __future__ import annotations

import re
from typing import Any

from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi

from rag.fusion import reciprocal_rank_fusion
from config import (
    DENSE_RETRIEVAL_K,
    DENSE_RETRIEVAL_FETCH_K,
    LAMBDA_MULT,
    SPARSE_RETRIEVAL_K,
)


def _tokenize(text: str) -> list[str]:
    """Small, deterministic tokenizer for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


def _all_documents(vectorstore: FAISS) -> list[Any]:
    """Read all chunks from the existing FAISS docstore.

    For this learning-oriented project, rebuilding the BM25 index in memory is
    intentionally simple. At large scale, use a persisted sparse index instead.
    """
    return [
        document
        for document in vectorstore.docstore._dict.values()
        if document is not None
    ]


def dense_retrieve(vectorstore: FAISS, query: str) -> list[tuple[Any, float]]:
    embedding = vectorstore.embeddings.embed_query(query)
    return vectorstore.max_marginal_relevance_search_with_score_by_vector(
        embedding,
        k=DENSE_RETRIEVAL_K,
        fetch_k=DENSE_RETRIEVAL_FETCH_K,
        lambda_mult=LAMBDA_MULT,
    )


def sparse_retrieve(vectorstore: FAISS, query: str) -> list[tuple[Any, float]]:
    """BM25 retrieval over chunks stored inside the notebook's FAISS docstore."""
    documents = _all_documents(vectorstore)
    if not documents:
        return []

    corpus_tokens = [_tokenize(doc.page_content) for doc in documents]
    bm25 = BM25Okapi(corpus_tokens)
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked_indices = sorted(
        range(len(documents)),
        key=lambda index: float(scores[index]),
        reverse=True,
    )[:SPARSE_RETRIEVAL_K]

    return [(documents[index], float(scores[index])) for index in ranked_indices]



def retrieve(vectorstore: FAISS, query: str) -> list[tuple[Any, float]]:
    """Backward-compatible dense-only retrieval helper."""
    return dense_retrieve(vectorstore, query)
