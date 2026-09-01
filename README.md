# JERRY.AI — Production-style Local RAG

JERRY.AI is a conversational Retrieval-Augmented Generation (RAG) application built without Streamlit.

The frontend uses plain **HTML/CSS/JavaScript**, while the backend is built with **FastAPI**. The RAG pipeline remains modular Python code and is exposed through a small HTTP API.

The current learning version extends the original semantic RAG pipeline with a more advanced **two-stage hybrid retrieval architecture**:

```text
Dense Retrieval + Sparse Retrieval
              ↓
             RRF
              ↓
       Candidate Documents
              ↓
        Cross-Encoder
          Reranking
              ↓
           Top-K
              ↓
         Context + History
              ↓
             LLM
              ↓
       Grounded Answer
              ↓
          Citations
```

The project is designed to demonstrate how a basic RAG application can gradually evolve into a more production-oriented retrieval system.

---

# Architecture

```text
Browser
  │
  │ fetch()
  ▼
FastAPI
  ├── SQLite
  │   ├── notebooks
  │   ├── messages
  │   ├── sources
  │   └── citations
  │
  ├── Document Ingestion
  │   ├── PDF
  │   ├── DOCX
  │   ├── TXT
  │   └── Markdown
  │
  ├── Gemini Embeddings
  │
  ├── Persistent FAISS
  │
  ├── BM25 Sparse Retrieval
  │
  ├── Hybrid Retrieval + RRF
  │
  ├── Cross-Encoder Reranker
  │
  └── Groq LLM
```

FastAPI serves the frontend itself, so the normal local setup uses a single process with same-origin requests.

---

# Project Structure

```text
.
├── backend/
│   ├── main.py
│   ├── schemas.py
│   └── services.py
│
├── database/
│   └── db.py
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── llm/
│   ├── model.py
│   └── prompt.py
│
├── rag/
│   ├── pipeline.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── fusion.py
│   └── vectorstore.py
│
├── data/
│
├── storage/
│   ├── uploads/
│   └── vectorstores/
│
├── config.py
├── requirements.txt
├── .env.example
└── README.md
```

---

# Environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_key
```

## Basic Configuration

```env
LLM_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=models/gemini-embedding-001

CHUNK_SIZE=1000
CHUNK_OVERLAP=150

MAX_HISTORY_MESSAGES=12
MAX_FILE_SIZE_MB=20
```

## Retrieval Configuration

The original application used MMR-based semantic retrieval.

The upgraded version separates the retrieval candidate pool from the final context size:

```env
DENSE_RETRIEVAL_K=20
DENSE_RETRIEVAL_FETCH_K=40

SPARSE_RETRIEVAL_K=20

RRF_K=60

CANDIDATE_K=20
FINAL_TOP_K=4
```

## Reranker Configuration

```env
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANKER_BATCH_SIZE=16
```

---

# Run the Application

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# API

Available endpoints:

```text
GET    /api/health

GET    /api/notebooks
POST   /api/notebooks

GET    /api/notebooks/{id}
DELETE /api/notebooks/{id}

GET    /api/notebooks/{id}/sources
POST   /api/notebooks/{id}/sources
DELETE /api/notebooks/{id}/sources/{source_id}

GET    /api/notebooks/{id}/messages
POST   /api/notebooks/{id}/chat
```

---

# Original RAG Flow

The original version of JERRY.AI used semantic retrieval directly before generation:

```text
Upload File
    ↓
Document Loader
    ↓
Recursive Character Splitting
    ↓
Gemini Embeddings
    ↓
Persistent FAISS Index
```

For a question:

```text
Question
    ↓
Gemini Embedding
    ↓
FAISS + MMR Retrieval
    ↓
Context Builder
    ↓
Chat History
    ↓
Groq LLM
    ↓
Answer + Citations
```

MMR was used to improve diversity among retrieved results.

---

# Advanced RAG Retrieval Pipeline

The current version introduces a two-stage retrieval architecture.

```text
                         Question
                            │
                            ▼
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       Dense Retrieval             Sparse Retrieval
        FAISS + MMR                     BM25
              │                           │
              └─────────────┬─────────────┘
                            ▼
                    Reciprocal Rank
                       Fusion (RRF)
                            │
                            ▼
                     Candidate-K
                       Documents
                            │
                            ▼
                  Cross-Encoder Reranker
                            │
                            ▼
                       Final Top-K
                            │
                            ▼
                  Context + Chat History
                            │
                            ▼
                          Groq
                            │
                            ▼
                  Grounded Answer
                            │
                            ▼
                         Citations
```

---

# Why the Retrieval Pipeline Has Multiple Stages

## 1. Dense Retrieval

Dense retrieval uses embeddings to identify documents that are semantically similar to the user's question.

```text
Question
   ↓
Embedding
   ↓
Vector
   ↓
FAISS
   ↓
Semantic Candidates
```

Dense retrieval is useful for understanding meaning, paraphrases, and related concepts.

---

# 2. MMR Retrieval

MMR stands for **Maximal Marginal Relevance**.

It helps balance:

```text
Relevance
+
Diversity
```

instead of returning many nearly identical chunks.

The project keeps configurable retrieval parameters for this behavior.

---

# 3. Sparse Retrieval with BM25

BM25 provides a keyword-oriented retrieval path.

```text
Question
   ↓
BM25
   ↓
Keyword-based Candidates
```

This is useful for:

* exact terms
* rare words
* identifiers
* product names
* technical terminology
* keyword-heavy questions

---

# 4. Hybrid Retrieval

Instead of trusting only one retrieval strategy, JERRY.AI combines:

```text
Dense Retrieval
      +
Sparse Retrieval
```

The result is a broader and more diverse candidate pool.

```text
FAISS
  \
   \
    → Hybrid Candidate Pool
   /
  /
BM25
```

---

# 5. Reciprocal Rank Fusion (RRF)

Dense and BM25 retrieval systems produce different ranking scores, so their raw scores should not simply be added together.

RRF combines their **rank positions** instead.

Conceptually:

```text
Dense Results
   ↓
Rank positions
   \
    \
     → RRF → Combined Ranking
    /
   /
Sparse Results
   ↓
Rank positions
```

The RRF score is based on the position of a document in each retrieval result list.

A commonly used form is:

```text
RRF(d) = Σ 1 / (k + rank(d))
```

A document that appears highly ranked in multiple retrieval systems receives a stronger combined ranking.

---

# 6. Candidate-K

The upgraded pipeline separates:

```text
Candidate-K
```

from:

```text
Final Top-K
```

For example:

```text
Hybrid Retrieval
      ↓
20 candidate documents
      ↓
Reranker
      ↓
4 final documents
      ↓
LLM
```

Configured as:

```env
CANDIDATE_K=20
FINAL_TOP_K=4
```

The reason for this separation is:

```text
Retriever → maximize recall

Reranker → improve precision

LLM → generate answer
```

A reranker cannot select a document that the retriever never retrieved.

---

# 7. Cross-Encoder Reranking

After retrieval and RRF, the candidate documents are passed to a cross-encoder reranker.

Instead of separately embedding the query and document, the reranker evaluates:

```text
Query + Document
```

together.

Conceptually:

```text
Query + Document A
        ↓
    Reranker
        ↓
     Score

Query + Document B
        ↓
    Reranker
        ↓
     Score
```

The candidates are then sorted by relevance.

```text
Candidate 20
     ↓
Cross-Encoder
     ↓
Ranked Candidates
     ↓
Top 4
```

This gives the LLM a cleaner context than using the initial retrieval ranking alone.

---

# 8. Final Context

After reranking:

```text
Reranked Documents
        ↓
     Top-K
        ↓
Context Builder
        +
Chat History
        ↓
       LLM
```

The project continues to use grounded generation so that the answer is based on the supplied context.

---

# 9. Citations

JERRY.AI keeps source-level metadata for retrieved chunks.

The final response can therefore identify:

```text
Source File
+
Chunk Information
```

This makes answers more traceable and easier to inspect.

---

# Complete RAG Flow

```text
                    ┌──────────────────┐
                    │    User Query    │
                    └────────┬─────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │    Query Processing   │
                 └───────────┬───────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
       ┌─────────────────┐       ┌─────────────────┐
       │ Dense Retrieval │       │ Sparse Retrieval│
       │   FAISS + MMR   │       │      BM25       │
       └────────┬────────┘       └────────┬────────┘
                │                         │
                └────────────┬────────────┘
                             ▼
                 ┌───────────────────────┐
                 │          RRF          │
                 │  Rank Fusion Layer    │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │    Candidate-K=20     │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Cross-Encoder         │
                 │ Re-Ranker             │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │     Final Top-K=4     │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Context Engineering  │
                 │ + Chat History       │
                 └───────────┬───────────┘
                             │
                             ▼
                       ┌───────────┐
                       │    Groq   │
                       │    LLM    │
                       └─────┬─────┘
                             │
                             ▼
                    Grounded Answer
                             │
                             ▼
                         Citations
```

---

# Why This Is Better Than Basic RAG

Basic RAG:

```text
Question
   ↓
Vector Search
   ↓
Top-K
   ↓
LLM
```

Advanced JERRY.AI:

```text
Question
   ↓
Dense + Sparse Retrieval
   ↓
RRF
   ↓
Large Candidate Pool
   ↓
Cross-Encoder Reranking
   ↓
Small High-Quality Context
   ↓
LLM
```

The important engineering principle is:

```text
Retrieval → Recall
Reranking → Precision
Generation → Answer
```

---

# Current Learning Architecture

This version is intentionally designed as a learning progression.

```text
                BASIC RAG
                   │
                   ▼
             FAISS + MMR
                   │
                   ▼
             HYBRID SEARCH
             ┌─────┴─────┐
             ▼           ▼
           FAISS        BM25
             └─────┬─────┘
                   ▼
                  RRF
                   │
                   ▼
              Candidate-K
                   │
                   ▼
               Reranker
                   │
                   ▼
                Top-K
                   │
                   ▼
                 LLM
```

This makes it possible to compare each retrieval improvement independently.

---

# Storage

The application stores:

```text
storage/
├── uploads/
└── vectorstores/
```

FAISS indexes are maintained per notebook so that notebook documents remain isolated.

SQLite stores:

```text
Notebooks
Sources
Messages
Citations
```

---

# Security Note

FAISS `load_local()` uses serialized local metadata.

Therefore:

```text
allow_dangerous_deserialization=True
```

is enabled only for indexes written by this application under:

```text
storage/vectorstores
```

Do not load arbitrary FAISS index files from untrusted sources.

Uploaded documents should also be treated as untrusted input when future agentic retrieval or tool-calling capabilities are added.

---

# Sparse Index Design Note

For learning simplicity, the BM25 index is rebuilt in memory from the notebook's FAISS document store.

This is appropriate for understanding the hybrid retrieval architecture.

For a large production corpus, a dedicated persistent sparse index should be maintained instead of rebuilding BM25 for every application lifecycle or request.

---

# Streamlit

Streamlit has been removed from the application and requirements.

The application now uses:

```text
HTML
+
CSS
+
JavaScript
+
FastAPI
```

The old Streamlit `app.py` is intentionally not included.

---

# Current Feature Set

```text
✅ FastAPI backend
✅ HTML/CSS/JavaScript frontend
✅ PDF ingestion
✅ DOCX ingestion
✅ TXT ingestion
✅ Markdown ingestion
✅ Recursive chunking
✅ Configurable chunk size
✅ Configurable chunk overlap
✅ Gemini embeddings
✅ Persistent FAISS vector stores
✅ MMR retrieval
✅ BM25 sparse retrieval
✅ Hybrid retrieval
✅ Reciprocal Rank Fusion
✅ Candidate-K retrieval
✅ Cross-Encoder reranking
✅ Final Top-K selection
✅ Context engineering
✅ Persistent conversation history
✅ SQLite persistence
✅ Source-level citations
✅ Grounded answers
✅ Notebook/source management
✅ File validation
✅ Vector cleanup on deletion
✅ REST API
✅ Swagger/OpenAPI documentation
```

---

# Planned Advanced RAG Features

The current version establishes the retrieval and reranking foundation.

The next possible learning stages are:

```text
1. Query Rewriting
2. Query Expansion
3. Multi-Query Retrieval
4. Query Decomposition
5. HyDE
6. Self-Query Retrieval
7. Semantic Chunking
8. Parent-Child Retrieval
9. Contextual Chunking
10. Context Compression
11. Context Deduplication
12. Retrieval Evaluation
13. RAG Evaluation
14. LangGraph Agentic Retrieval
15. Context Grading
16. Retry / Rewrite Loops
17. Adaptive Retrieval
18. Semantic Caching
19. Observability
20. RAG Security
```

---

# Goal of the Project

JERRY.AI is not intended to be only a document chatbot.

The project is being developed as a practical progression from:

```text
Basic RAG
   ↓
Better Retrieval
   ↓
Hybrid Retrieval
   ↓
Reranking
   ↓
Context Engineering
   ↓
Evaluation
   ↓
Agentic RAG
   ↓
Production AI System
```

The main engineering principle is:

> **Better answers start with better context.**
>
> The goal is therefore not simply to use a larger LLM, but to build a retrieval system that finds, ranks, and supplies the right information to the model.
