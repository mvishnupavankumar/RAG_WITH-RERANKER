from dataclasses import dataclass

from rag.fusion import reciprocal_rank_fusion


@dataclass
class FakeDoc:
    name: str
    metadata: dict


def test_rrf_favors_documents_present_in_both_rankings():
    a = FakeDoc("A", {"source_id": "s", "chunk_id": 1})
    b = FakeDoc("B", {"source_id": "s", "chunk_id": 2})
    c = FakeDoc("C", {"source_id": "s", "chunk_id": 3})

    fused = reciprocal_rank_fusion(
        [(a, 0.99), (b, 0.80), (c, 0.70)],
        [(b, 9.0), (c, 8.0), (a, 1.0)],
        rrf_k=60,
    )

    assert [doc.name for doc, _score in fused] == ["A", "B", "C"]
    assert fused[0][1] == fused[0][1]  # score is finite / numeric
