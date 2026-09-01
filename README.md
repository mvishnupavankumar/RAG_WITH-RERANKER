# JERRY.AI — Production-style Local RAG

JERRY.AI is a conversational RAG application built without Streamlit.
The frontend is plain HTML/CSS/JavaScript and the backend is FastAPI. The existing RAG modules remain in Python and are exposed through a small HTTP API.

## Architecture

```text
Browser
  │
  │ fetch()
  ▼
FastAPI
  ├── SQLite: notebooks, messages, sources, citations
  ├── Ingestion: PDF / DOCX / TXT / MD
  ├── Gemini embeddings
  ├── Persistent FAISS per notebook
  └── Groq LLM
```

FastAPI serves the frontend itself, so the normal local setup is a single process and same-origin requests.

## Project structure

```text
.
├── backend/
│   ├── main.py
│   ├── schemas.py
│   └── services.py
├── database/
│   └── db.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── llm/
│   ├── model.py
│   └── prompt.py
├── rag/
│   ├── pipeline.py
│   ├── retriever.py
│   └── vectorstore.py
├── data/
├── storage/
│   ├── uploads/
│   └── vectorstores/
├── config.py
└── requirements.txt
```

## Environment

Create `.env`:

```env
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_key
```

Optional configuration:

```env
LLM_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=models/gemini-embedding-001
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
RETRIEVER_K=4
RETRIEVER_FETCH_K=12
LAMBDA_MULT=0.5
MAX_HISTORY_MESSAGES=12
MAX_FILE_SIZE_MB=20
```

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## API

- `GET /api/health`
- `GET /api/notebooks`
- `POST /api/notebooks`
- `GET /api/notebooks/{id}`
- `DELETE /api/notebooks/{id}`
- `GET /api/notebooks/{id}/sources`
- `POST /api/notebooks/{id}/sources`
- `DELETE /api/notebooks/{id}/sources/{source_id}`
- `GET /api/notebooks/{id}/messages`
- `POST /api/notebooks/{id}/chat`

## RAG flow

```text
Upload file
   ↓
Loader
   ↓
Chunking
   ↓
Gemini embedding
   ↓
Persistent FAISS index for that notebook

Question
   ↓
Gemini embedding
   ↓
MMR retrieval
   ↓
Context builder
   ↓
Groq
   ↓
Answer + citations
```

## Important security note

FAISS `load_local()` uses serialized local metadata, so this project enables `allow_dangerous_deserialization=True` only for indexes written by this application under `storage/vectorstores`. Do not load arbitrary FAISS index files from untrusted sources.

## Streamlit

Streamlit has been removed from the application and requirements. The old Streamlit `app.py` is intentionally not included.

## Advanced RAG retrieval pipeline

The original project used MMR retrieval directly before generation. The current learning version upgrades retrieval to a two-stage hybrid pipeline:

```text
Question
   ↓
┌───────────────┬────────────────┐
│ Dense         │ Sparse         │
│ FAISS + MMR   │ BM25           │
└───────┬───────┴───────┬────────┘
        └───────┬───────┘
                ↓
        Reciprocal Rank Fusion
                ↓
         Candidate-K (20)
                ↓
        Cross-Encoder Reranker
                ↓
            Final Top-K
                ↓
          Context + History
                ↓
               LLM
                ↓
         Grounded answer + citations
```

### Why these stages exist

- **Dense retrieval** captures semantic meaning.
- **BM25** captures exact words and rare terms.
- **RRF** combines the rankings without assuming FAISS and BM25 scores use the same numeric scale.
- **Candidate-K** keeps recall high before the expensive ranking step.
- **Cross-encoder reranking** reads the query and candidate document together and improves precision.
- **Final Top-K** limits the context sent to the LLM.

### New environment settings

```env
DENSE_RETRIEVAL_K=20
DENSE_RETRIEVAL_FETCH_K=40
SPARSE_RETRIEVAL_K=20
RRF_K=60
CANDIDATE_K=20
FINAL_TOP_K=4
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_BATCH_SIZE=16
```

The BM25 index is intentionally rebuilt in memory from the notebook's FAISS docstore for simplicity while learning. For a large production corpus, persist and maintain a dedicated sparse index instead.
