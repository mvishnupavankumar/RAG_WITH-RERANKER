from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "storage" / "jerry.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "storage" / "uploads"))
VECTORSTORE_DIR = Path(os.getenv("VECTORSTORE_DIR", BASE_DIR / "storage" / "vectorstores"))
FRONTEND_DIR = BASE_DIR / "frontend"

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))

RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))
RETRIEVER_FETCH_K = int(os.getenv("RETRIEVER_FETCH_K", "12"))
LAMBDA_MULT = float(os.getenv("LAMBDA_MULT", "0.5"))

# Advanced retrieval / ranking pipeline
DENSE_RETRIEVAL_K = int(os.getenv("DENSE_RETRIEVAL_K", "20"))
DENSE_RETRIEVAL_FETCH_K = int(os.getenv("DENSE_RETRIEVAL_FETCH_K", "40"))
SPARSE_RETRIEVAL_K = int(os.getenv("SPARSE_RETRIEVAL_K", "20"))
RRF_K = int(os.getenv("RRF_K", "60"))
CANDIDATE_K = int(os.getenv("CANDIDATE_K", "20"))
FINAL_TOP_K = int(os.getenv("FINAL_TOP_K", str(RETRIEVER_K)))
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_BATCH_SIZE = int(os.getenv("RERANKER_BATCH_SIZE", "16"))
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

ALLOWED_FILE_TYPES = {
    ".pdf": "PDF",
    ".txt": "TXT",
    ".md": "MD",
    ".docx": "DOCX",
}

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if origin.strip()
]

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
