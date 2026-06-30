from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from ..config import DB_PATH, SCHEMA_PATH, ensure_directories

SCHEMA_VERSION = 1
_local = threading.local()


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")


def get_connection() -> sqlite3.Connection:
    conn = getattr(_local, "connection", None)
    if conn is None:
        ensure_directories()
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _configure_connection(conn)
        _local.connection = conn
    return conn


@contextmanager
def db_cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def init_database() -> None:
    ensure_directories()
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db_cursor() as cur:
        cur.executescript(schema_sql)
        row = cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            cur.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        elif row["version"] < SCHEMA_VERSION:
            cur.execute(
                "UPDATE schema_version SET version = ?",
                (SCHEMA_VERSION,),
            )


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with db_cursor() as cur:
        return list(cur.execute(query, params).fetchall())


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    with db_cursor() as cur:
        return cur.execute(query, params).fetchone()


def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with db_cursor() as cur:
        cur.execute(query, params)


def mark_interrupted_jobs() -> int:
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
            SET status = 'interrupted', finished_at = COALESCE(finished_at, datetime('now'))
            WHERE status IN ('running', 'queued')
            """
        )
        return cur.rowcount
