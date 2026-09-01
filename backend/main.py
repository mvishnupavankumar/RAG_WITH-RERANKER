from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.schemas import ChatRequest, CreateNotebookRequest
from backend.services import (
    chat,
    create,
    history,
    notebook,
    notebooks,
    remove_notebook,
    remove_source,
    sources,
    upload_source,
)
from config import FRONTEND_DIR
from database.db import init_db

logger = logging.getLogger("jerry-ai")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="JERRY.AI", version="1.0.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "jerry-ai"}


@app.get("/api/notebooks")
def get_notebooks() -> list[dict]:
    return notebooks()


@app.post("/api/notebooks")
def post_notebook(request: CreateNotebookRequest) -> dict:
    return create(request.name)


@app.get("/api/notebooks/{notebook_id}")
def get_notebook(notebook_id: int) -> dict:
    return notebook(notebook_id)


@app.delete("/api/notebooks/{notebook_id}")
def delete_nb(notebook_id: int) -> None:
    remove_notebook(notebook_id)
    return {"message": "Notebook deleted"}


@app.get("/api/notebooks/{notebook_id}/sources")
def get_sources(notebook_id: int) -> list[dict]:
    return sources(notebook_id)


@app.post("/api/notebooks/{notebook_id}/sources", status_code=201)
async def post_source(notebook_id: int, file: UploadFile = File(...)) -> dict:
    return await asyncio.to_thread(upload_source, notebook_id, file)


@app.delete("/api/notebooks/{notebook_id}/sources/{source_id}")
def delete_src(notebook_id: int, source_id: str) -> None:
    remove_source(notebook_id, source_id)
    return {"message": "Source deleted"}


@app.get("/api/notebooks/{notebook_id}/messages")
def get_history(notebook_id: int) -> list[dict]:
    return history(notebook_id)


@app.post("/api/notebooks/{notebook_id}/chat")
async def post_chat(notebook_id: int, request: ChatRequest) -> dict:
    return await asyncio.to_thread(chat, notebook_id, request.question.strip())


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def missing_frontend() -> dict:
        raise HTTPException(status_code=500, detail="Frontend directory is missing")
