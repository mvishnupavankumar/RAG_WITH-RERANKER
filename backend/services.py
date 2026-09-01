from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from langchain_core.messages import AIMessage, HumanMessage

from config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB, MAX_HISTORY_MESSAGES, UPLOAD_DIR, VECTORSTORE_DIR
from database.db import (
    add_citations,
    add_message,
    create_notebook,
    create_source,
    update_source_detail,
    delete_notebook,
    delete_source,
    get_notebook,
    get_source,
    list_messages,
    list_notebooks,
    list_sources,
    citations_for_messages,
)
from rag.pipeline import conversational_rag
from rag.vectorstore import delete_source_vectors, ingest_file, load_vectorstore

logger = logging.getLogger("jerry-ai.services")


def notebooks() -> list[dict]:
    return list_notebooks()


def notebook(notebook_id: int) -> dict:
    item = get_notebook(notebook_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notebook not found")
    item["sources"] = list_sources(notebook_id)
    return item


def create(name: str) -> dict:
    return create_notebook(name)


def remove_notebook(notebook_id: int) -> None:
    item = get_notebook(notebook_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notebook not found")

    delete_notebook(notebook_id)

    vector_dir = VECTORSTORE_DIR / f"notebook_{notebook_id}"
    upload_dir = UPLOAD_DIR / str(notebook_id)
    if vector_dir.exists():
        shutil.rmtree(vector_dir, ignore_errors=True)
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)


def sources(notebook_id: int) -> list[dict]:
    notebook(notebook_id)
    return list_sources(notebook_id)


def upload_source(notebook_id: int, file: UploadFile) -> dict:
    notebook(notebook_id)

    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if not original_name or suffix not in ALLOWED_FILE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_FILE_TYPES))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")

    source_id = str(uuid.uuid4())
    target_dir = UPLOAD_DIR / str(notebook_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{source_id}{suffix}"

    size = 0
    try:
        with target_path.open("wb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit",
                    )
                output.write(chunk)

        source_type = ALLOWED_FILE_TYPES[suffix]
        source = create_source(
            source_id=source_id,
            notebook_id=notebook_id,
            source_type=source_type,
            title=original_name,
            detail="Indexed just now",
            file_path=str(target_path),
        )

        chunk_count = ingest_file(notebook_id, source_id, str(target_path), original_name)
        detail = f"{chunk_count} chunks indexed"
        update_source_detail(source_id, detail)
        source["detail"] = detail
        return source

    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        delete_source(source_id)
        logger.exception("Source indexing failed", extra={"notebook_id": notebook_id, "source_id": source_id})
        raise HTTPException(status_code=500, detail="Failed to index source") from exc


def remove_source(notebook_id: int, source_id: str) -> None:
    source = get_source(source_id)
    if not source or source["notebook_id"] != notebook_id:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        delete_source_vectors(notebook_id, source_id)
        delete_source(source_id)
        if source.get("file_path"):
            Path(source["file_path"]).unlink(missing_ok=True)
    except Exception as exc:
        logger.exception("Source deletion failed", extra={"notebook_id": notebook_id, "source_id": source_id})
        raise HTTPException(status_code=500, detail="Failed to remove source") from exc


def history(notebook_id: int) -> list[dict]:
    notebook(notebook_id)
    messages = list_messages(notebook_id)
    citation_map = citations_for_messages(notebook_id)
    for message in messages:
        message["citations"] = citation_map.get(message["id"], [])
    return messages


def chat(notebook_id: int, question: str) -> dict:
    notebook(notebook_id)
    vectorstore = load_vectorstore(notebook_id)

    stored = list_messages(notebook_id)
    history_messages = []
    for message in stored[-MAX_HISTORY_MESSAGES:]:
        if message["role"] == "human":
            history_messages.append(HumanMessage(content=message["content"]))
        else:
            history_messages.append(AIMessage(content=message["content"]))

    human_message_id = add_message(notebook_id, "human", question)
    history_messages.append(HumanMessage(content=question))

    answer, citations = conversational_rag(question, history_messages, vectorstore)
    ai_message_id = add_message(notebook_id, "ai", answer)
    add_citations(ai_message_id, citations)

    return {
        "message_id": ai_message_id,
        "answer": answer,
        "citations": citations,
        "user_message_id": human_message_id,
    }
