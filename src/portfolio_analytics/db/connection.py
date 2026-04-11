"""
Database connection management for SQLite.

Provides a thin wrapper that:
    • Creates the schema on first use.
    • Returns plain ``sqlite3.Connection`` objects (thread-safe via WAL mode).
    • Is easily replaceable by a PostgreSQL pool in a future iteration.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from portfolio_analytics.db.schema import SCHEMA_SQL

_DEFAULT_DB_PATH = Path("portfolio_analytics.sqlite3")


class Database:
    """Manages a single SQLite database file."""

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = str(db_path)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        """Return a new connection with recommended pragmas."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def reset(self) -> None:
        """Drop all tables and recreate schema (useful in tests)."""
        conn = self.connect()
        try:
            for table in (
                "instrument_attributes_history",
                "transactions",
                "cash_accounts",
                "instruments",
                "portfolios",
                "clients",
            ):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        conn = self.connect()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()
