from __future__ import annotations

import os
import threading
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    UPLOAD_DIR,
    VECTORSTORE_DIR,
)

_locks: dict[int, threading.RLock] = {}
_locks_guard = threading.Lock()


def get_notebook_lock(notebook_id: int) -> threading.RLock:
    with _locks_guard:
        if notebook_id not in _locks:
            _locks[notebook_id] = threading.RLock()
        return _locks[notebook_id]


def _store_path(notebook_id: int) -> Path:
    return VECTORSTORE_DIR / f"notebook_{notebook_id}"


def _embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)


def _loader(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path))
    if suffix in {".txt", ".md"}:
        return TextLoader(str(path), encoding="utf-8")
    if suffix == ".docx":
        return Docx2txtLoader(str(path))
    raise ValueError(f"Unsupported file type: {suffix}")


def _split_documents(documents: list[Document], source_id: str, source_name: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    total_chunks = len(chunks)

    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata.update(
            {
                "source_id": source_id,
                "source": source_name,
                "chunk_id": index,
                "total_chunks": total_chunks,
            }
        )

    return chunks


def ingest_file(notebook_id: int, source_id: str, file_path: str, source_name: str) -> int:
    path = Path(file_path)
    documents = _loader(path).load()
    chunks = _split_documents(documents, source_id, source_name)
    if not chunks:
        raise ValueError("No text could be extracted from the source")

    store_path = _store_path(notebook_id)
    lock = get_notebook_lock(notebook_id)

    with lock:
        embeddings = _embeddings()

        if store_path.exists():
            vectorstore = FAISS.load_local(
                str(store_path),
                embeddings,
                allow_dangerous_deserialization=True,
                normalize_L2=True,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
            ids = [f"{source_id}:{i}" for i in range(1, len(chunks) + 1)]
            vectorstore.add_documents(chunks, ids=ids)
        else:
            ids = [f"{source_id}:{i}" for i in range(1, len(chunks) + 1)]
            vectorstore = FAISS.from_documents(
                chunks,
                embeddings,
                ids=ids,
                normalize_L2=True,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )

        store_path.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(store_path))

    return len(chunks)


def load_vectorstore(notebook_id: int) -> FAISS | None:
    store_path = _store_path(notebook_id)
    if not store_path.exists():
        return None

    lock = get_notebook_lock(notebook_id)
    with lock:
        return FAISS.load_local(
            str(store_path),
            _embeddings(),
            allow_dangerous_deserialization=True,
            normalize_L2=True,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )


def delete_source_vectors(notebook_id: int, source_id: str) -> None:
    store_path = _store_path(notebook_id)
    if not store_path.exists():
        return

    lock = get_notebook_lock(notebook_id)
    with lock:
        vectorstore = FAISS.load_local(
            str(store_path),
            _embeddings(),
            allow_dangerous_deserialization=True,
            normalize_L2=True,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )

        ids_to_delete: list[str] = []
        for doc_id in list(vectorstore.index_to_docstore_id.values()):
            document = vectorstore.docstore.search(doc_id)
            if document and document.metadata.get("source_id") == source_id:
                ids_to_delete.append(doc_id)

        if ids_to_delete:
            vectorstore.delete(ids=ids_to_delete)
            if len(vectorstore.index_to_docstore_id) == 0:
                for child in store_path.iterdir():
                    if child.is_file():
                        child.unlink()
                store_path.rmdir()
            else:
                vectorstore.save_local(str(store_path))
