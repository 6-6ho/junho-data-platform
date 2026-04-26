"""Postgres connection singleton.

Follows the pattern from apps/investment-agent/db.py — one long-lived autocommit
connection per process. The rag-server is a single-worker uvicorn process so a
singleton is fine. If we scale to multiple workers, switch to psycopg2.pool.
"""
from __future__ import annotations

import logging
from typing import Any

import psycopg2
from psycopg2.extensions import connection as Connection

from rag_server.config import settings

logger = logging.getLogger(__name__)

_conn: Connection | None = None


def get_conn() -> Connection:
    """Return a live autocommit connection, reconnecting if closed."""
    global _conn
    if _conn is None or _conn.closed:
        logger.info("connecting to postgres at %s:%s/%s", settings.db_host, settings.db_port, settings.db_name)
        _conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )
        _conn.autocommit = True
    return _conn


def execute(sql: str, params: tuple | None = None) -> None:
    """Fire-and-forget DDL/DML; raises on error."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)


def query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a SELECT and return rows as list of dicts."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description is None:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def query_one(sql: str, params: tuple | None = None) -> dict[str, Any] | None:
    """Execute a SELECT expected to return 0-or-1 rows."""
    rows = query(sql, params)
    return rows[0] if rows else None
