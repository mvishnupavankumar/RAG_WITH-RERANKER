from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import DATABASE_PATH

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS notebooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '✦',
    description TEXT NOT NULL DEFAULT 'Your sources and conversations',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    notebook_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT NOT NULL,
    file_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sources_notebook ON sources(notebook_id);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notebook_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('human', 'ai')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_notebook ON messages(notebook_id, id);

CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    citation_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    total_chunks TEXT NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_citations_message ON citations(message_id);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT COUNT(*) AS count FROM notebooks").fetchone()
        if row["count"] == 0:
            conn.execute(
                "INSERT INTO notebooks(name, icon, description) VALUES (?, ?, ?)",
                ("AI Engineering", "✦", "Explore your AI engineering sources"),
            )


def list_notebooks() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT n.id, n.name, n.icon, n.description, n.created_at,
                   COUNT(s.id) AS source_count
            FROM notebooks n
            LEFT JOIN sources s ON s.notebook_id = n.id
            GROUP BY n.id
            ORDER BY n.updated_at DESC, n.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_notebook(notebook_id: int) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, name, icon, description, created_at FROM notebooks WHERE id = ?",
            (notebook_id,),
        ).fetchone()
        return dict(row) if row else None


def create_notebook(name: str, description: str = "Your sources and conversations") -> dict:
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO notebooks(name, description) VALUES (?, ?)",
            (name.strip(), description.strip()),
        )
        notebook_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT id, name, icon, description, created_at FROM notebooks WHERE id = ?",
            (notebook_id,),
        ).fetchone()
        return dict(row)


def touch_notebook(notebook_id: int) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE notebooks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notebook_id,),
        )


def delete_notebook(notebook_id: int) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))


def list_sources(notebook_id: int) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, notebook_id, type, title, detail, created_at
            FROM sources
            WHERE notebook_id = ?
            ORDER BY id ASC
            """,
            (notebook_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def create_source(
    source_id: str,
    notebook_id: int,
    source_type: str,
    title: str,
    detail: str,
    file_path: str | None,
) -> dict:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO sources(id, notebook_id, type, title, detail, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source_id, notebook_id, source_type, title, detail, file_path),
        )
        conn.execute(
            "UPDATE notebooks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notebook_id,),
        )
        row = conn.execute(
            "SELECT id, notebook_id, type, title, detail, created_at FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return dict(row)


def update_source_detail(source_id: str, detail: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE sources SET detail = ? WHERE id = ?",
            (detail, source_id),
        )


def get_source(source_id: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, notebook_id, type, title, detail, file_path FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return dict(row) if row else None


def delete_source(source_id: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))


def add_message(notebook_id: int, role: str, content: str) -> int:
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO messages(notebook_id, role, content) VALUES (?, ?, ?)",
            (notebook_id, role, content),
        )
        conn.execute(
            "UPDATE notebooks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notebook_id,),
        )
        return int(cur.lastrowid)


def list_messages(notebook_id: int) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, notebook_id, role, content, created_at
            FROM messages
            WHERE notebook_id = ?
            ORDER BY id ASC
            """,
            (notebook_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def add_citations(message_id: int, citations: list[dict]) -> None:
    if not citations:
        return
    with connection() as conn:
        conn.executemany(
            """
            INSERT INTO citations(
                message_id, citation_id, source, chunk_id, total_chunks, content
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    message_id,
                    c["id"],
                    c["source"],
                    str(c["chunk_id"]),
                    str(c["total_chunks"]),
                    c["content"],
                )
                for c in citations
            ],
        )


def citations_for_messages(notebook_id: int) -> dict[int, list[dict]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.message_id, c.citation_id, c.source, c.chunk_id,
                   c.total_chunks, c.content
            FROM citations c
            JOIN messages m ON m.id = c.message_id
            WHERE m.notebook_id = ?
            ORDER BY c.message_id ASC, c.citation_id ASC
            """,
            (notebook_id,),
        ).fetchall()

    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row["message_id"], []).append(
            {
                "id": row["citation_id"],
                "source": row["source"],
                "chunk_id": row["chunk_id"],
                "total_chunks": row["total_chunks"],
                "content": row["content"],
            }
        )
    return result
