"""Local, file-based storage for the Operations Assistant.

Everything lives on the user's own PC. No data ever leaves the machine.

We use a small SQLite database (built into Python -- no extra software) kept
in the per-user application-data folder so it survives app updates and is not
wiped when the program is reinstalled.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone


APP_NAME = "OperationsAssistant"


def data_dir() -> str:
    """Return the folder where we keep the database and uploaded files.

    On Windows this is %APPDATA%\\OperationsAssistant, on other systems it
    falls back to ~/.local/share/OperationsAssistant so development on Linux
    or macOS works too.
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> str:
    return os.path.join(data_dir(), "knowledge.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the database tables on first run."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS qa_pairs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                question    TEXT NOT NULL,
                answer      TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                added_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id  INTEGER NOT NULL,
                ordinal      INTEGER NOT NULL,
                text         TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            """
        )


# --------------------------------------------------------------------------
# Q&A pairs
# --------------------------------------------------------------------------
def list_qa() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, question, answer, created_at, updated_at "
            "FROM qa_pairs ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_qa(question: str, answer: str) -> int:
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO qa_pairs (question, answer, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (question.strip(), answer.strip(), now, now),
        )
        return int(cur.lastrowid)


def update_qa(qa_id: int, question: str, answer: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE qa_pairs SET question = ?, answer = ?, updated_at = ? "
            "WHERE id = ?",
            (question.strip(), answer.strip(), _now(), qa_id),
        )


def delete_qa(qa_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM qa_pairs WHERE id = ?", (qa_id,))


# --------------------------------------------------------------------------
# Documents + their text chunks
# --------------------------------------------------------------------------
def list_documents() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT d.id, d.filename, d.added_at, COUNT(c.id) AS chunk_count "
            "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
            "GROUP BY d.id ORDER BY d.added_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_document(filename: str, chunks: list[str]) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO documents (filename, added_at) VALUES (?, ?)",
            (filename, _now()),
        )
        doc_id = int(cur.lastrowid)
        conn.executemany(
            "INSERT INTO chunks (document_id, ordinal, text) VALUES (?, ?, ?)",
            [(doc_id, i, text) for i, text in enumerate(chunks)],
        )
        return doc_id


def delete_document(doc_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


def all_chunks() -> list[dict]:
    """Return every document chunk with its source filename."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT c.id, c.text, d.filename "
            "FROM chunks c JOIN documents d ON d.id = c.document_id"
        ).fetchall()
    return [dict(r) for r in rows]
