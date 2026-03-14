import os

import psycopg

_conn: psycopg.Connection | None = None


def _get_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgres://itchy:itchy@localhost:5434/scratchy"
    )


def get_conn() -> psycopg.Connection:
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(_get_url(), autocommit=True)
    return _conn


def close():
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
        _conn = None
