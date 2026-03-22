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
        # future tables (cash_accounts, products, transactions) could be added
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
