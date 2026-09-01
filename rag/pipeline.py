from __future__ import annotations

import re
from typing import Iterable

from langchain_core.messages import BaseMessage

from config import CANDIDATE_K, FINAL_TOP_K, MAX_HISTORY_MESSAGES, RRF_K
from llm.model import get_llm
from llm.prompt import prompt
from rag.reranker import rerank
from rag.retriever import dense_retrieve, reciprocal_rank_fusion, sparse_retrieve


def _compact_history(history: Iterable[BaseMessage]) -> list[BaseMessage]:
    items = list(history)
    return items[-MAX_HISTORY_MESSAGES:]


def _retrieve_and_rerank(vectorstore, query: str):
    """Complete advanced retrieval path:

    dense + sparse -> RRF -> candidate pool -> cross-encoder reranker -> top K.
    """
    dense_results = dense_retrieve(vectorstore, query)
    sparse_results = sparse_retrieve(vectorstore, query)

    fused_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        sparse_results=sparse_results,
        rrf_k=RRF_K,
    )

    candidates = fused_results[:CANDIDATE_K]
    reranked = rerank(query, [doc for doc, _score in candidates])
    final_docs = reranked[:FINAL_TOP_K]

    return final_docs


def conversational_rag(
    user_input: str,
    chat_history: list[BaseMessage],
    vectorstore,
) -> tuple[str, list[dict]]:
    if vectorstore is None:
        messages = prompt.invoke(
            {
                "question": user_input,
                "context": "No documents have been uploaded to this notebook yet.",
                "chat_history": _compact_history(chat_history),
            }
        )
        response = get_llm().invoke(messages)
        return response.content, []

    docs_with_scores = _retrieve_and_rerank(vectorstore, user_input)

    citations = []
    context_blocks = []
    for index, (doc, score) in enumerate(docs_with_scores, start=1):
        source = doc.metadata.get("source", "Unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")
        total_chunks = doc.metadata.get("total_chunks", "?")

        context_blocks.append(
            f"[{index}] Source: {source} (Chunk {chunk_id}/{total_chunks})\n{doc.page_content}"
        )
        citations.append(
            {
                "id": index,
                "source": source,
                "chunk_id": chunk_id,
                "total_chunks": total_chunks,
                "content": doc.page_content,
                "score": round(float(score), 4),
            }
        )

    context = "\n\n".join(context_blocks) or "No relevant context found."

    messages = prompt.invoke(
        {
            "question": user_input,
            "context": context,
            "chat_history": _compact_history(chat_history),
        }
    )

    response = get_llm().invoke(messages)
    answer = response.content

    cited_ids = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    if cited_ids:
        used = [citation for citation in citations if citation["id"] in cited_ids]
    else:
        used = citations

    # Retrieval scores are backend diagnostics; keep them out of the user-facing citation card.
    for citation in used:
        citation.pop("score", None)

    return answer, used
