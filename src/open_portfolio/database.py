"""Simple SQLite storage for portfolio test data.

This module provides a very lightweight persistence layer using SQLite.  It is
intended primarily for capturing the objects created during tests or demos; it
is **not** a full-featured ORM.  Tables are created on demand and most fields
are stored as plain columns with a handful of JSON blobs where needed.

Usage example::

    from open_portfolio.database import Database
    from open_portfolio.clients import Client

    db = Database("data.sqlite")
    client = Client(1, "Alice")
    portfolio = client.add_portfolio(1)
    db.add_client(client)
    db.add_portfolio(portfolio)

    print(db.get_clients())
    print(db.get_portfolios())

"""

import sqlite3
import json
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, List, Optional

class Database:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        # clients and portfolios are the only two tables we currently need
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS client (
                client_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                portfolio_id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                name TEXT,
                default_currency TEXT,
                cost_in_transaction_currency INTEGER
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS order_draft (
                draft_id TEXT PRIMARY KEY,
                portfolio_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                errors_json TEXT,
                warnings_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    # simple insert/replace helpers
    def add_client(self, client: Any) -> None:
        """Store a :class:`~open_portfolio.clients.Client` in the database."""
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO client(client_id, name) VALUES (?, ?)" ,
            (client.client_id, client.name),
        )
        self.conn.commit()

    def add_portfolio(self, portfolio: Any) -> None:
        """Store a :class:`~open_portfolio.accounts.Portfolio` in the database."""
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO portfolio(portfolio_id, client_id, name, default_currency, cost_in_transaction_currency) VALUES (?, ?, ?, ?, ?)",
            (
                portfolio.portfolio_id,
                portfolio.client_id,
                portfolio.name,
                portfolio.default_currency,
                1 if portfolio.cost_in_transaction_currency else 0,
            ),
        )
        self.conn.commit()

    # retrieval helpers
    def get_clients(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("SELECT client_id, name FROM client")
        rows = c.fetchall()
        return [{"client_id": r[0], "name": r[1]} for r in rows]

    def get_portfolios(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute(
            "SELECT portfolio_id, client_id, name, default_currency, cost_in_transaction_currency FROM portfolio"
        )
        rows = c.fetchall()
        return [
            {
                "portfolio_id": r[0],
                "client_id": r[1],
                "name": r[2],
                "default_currency": r[3],
                "cost_in_transaction_currency": bool(r[4]),
            }
            for r in rows
        ]

    def close(self):
        self.conn.close()

    def upsert_order_draft(
        self,
        draft_id: str,
        portfolio_id: int,
        status: str,
        payload: Dict[str, Any],
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        created_value = created_at or now
        updated_value = updated_at or now
        c = self.conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO order_draft(
                draft_id,
                portfolio_id,
                status,
                payload_json,
                errors_json,
                warnings_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                portfolio_id,
                status,
                json.dumps(payload),
                json.dumps(errors or []),
                json.dumps(warnings or []),
                created_value,
                updated_value,
            ),
        )
        self.conn.commit()

    def get_order_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute(
            """
            SELECT draft_id, portfolio_id, status, payload_json, errors_json, warnings_json, created_at, updated_at
            FROM order_draft
            WHERE draft_id = ?
            """,
            (draft_id,),
        )
        row = c.fetchone()
        if row is None:
            return None
        return {
            "draft_id": row[0],
            "portfolio_id": row[1],
            "status": row[2],
            "payload": json.loads(row[3] or "{}"),
            "errors": json.loads(row[4] or "[]"),
            "warnings": json.loads(row[5] or "[]"),
            "created_at": row[6],
            "updated_at": row[7],
        }

    def purge_stale_order_drafts(
        self,
        retention_days: int,
        statuses: Optional[List[str]] = None,
    ) -> int:
        if retention_days <= 0:
            return 0

        status_filter = statuses or ["draft", "validated", "rejected"]
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        cutoff_iso = cutoff.isoformat(timespec="seconds")

        placeholders = ",".join(["?"] * len(status_filter))
        query = (
            f"DELETE FROM order_draft WHERE created_at < ? "
            f"AND status IN ({placeholders})"
        )

        c = self.conn.cursor()
        c.execute(query, [cutoff_iso] + status_filter)
        deleted = c.rowcount if c.rowcount is not None else 0
        self.conn.commit()
        return deleted

    def get_order_draft_status_counts(self) -> Dict[str, int]:
        c = self.conn.cursor()
        c.execute(
            """
            SELECT status, COUNT(*)
            FROM order_draft
            GROUP BY status
            """
        )
        rows = c.fetchall()
        return {str(r[0]): int(r[1]) for r in rows}

    def list_order_drafts(self, limit: int = 100) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        c = self.conn.cursor()
        c.execute(
            """
            SELECT draft_id, portfolio_id, status, payload_json, errors_json, warnings_json, created_at, updated_at
            FROM order_draft
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        )
        rows = c.fetchall()
        return [
            {
                "draft_id": r[0],
                "portfolio_id": r[1],
                "status": r[2],
                "payload": json.loads(r[3] or "{}"),
                "errors": json.loads(r[4] or "[]"),
                "warnings": json.loads(r[5] or "[]"),
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]
