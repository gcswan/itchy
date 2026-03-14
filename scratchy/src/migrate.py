"""File-based SQL migrations tracked via a _migrations table."""

import os
from pathlib import Path

import psycopg


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def run_migrations(conn: psycopg.Connection) -> list[str]:
    """Run all pending migrations. Returns list of applied migration filenames."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    applied = {
        row[0]
        for row in conn.execute("SELECT filename FROM _migrations").fetchall()
    }

    sql_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
    )

    newly_applied = []
    for filename in sql_files:
        if filename in applied:
            continue
        sql = (MIGRATIONS_DIR / filename).read_text()
        conn.execute(sql)
        conn.execute(
            "INSERT INTO _migrations (filename) VALUES (%s)", (filename,)
        )
        newly_applied.append(filename)

    return newly_applied
