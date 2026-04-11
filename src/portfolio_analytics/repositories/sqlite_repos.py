"""
SQLite implementations of all repository contracts.

Each repository receives a ``Database`` instance and uses plain SQL.
Row results are mapped to domain models via private helper methods.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from portfolio_analytics.db.connection import Database
from portfolio_analytics.domain.enums import InstrumentType, TransactionType
from portfolio_analytics.domain.models import (
    CashAccount,
    Client,
    Instrument,
    InstrumentAttributeHistory,
    Portfolio,
    Transaction,
)
from portfolio_analytics.repositories.base import (
    CashAccountRepository,
    ClientRepository,
    InstrumentRepository,
    PortfolioRepository,
    TransactionRepository,
)


# ===================================================================
# Helpers
# ===================================================================

def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _from_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


# ===================================================================
# Client
# ===================================================================


class SqliteClientRepository(ClientRepository):

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, client: Client) -> None:
        conn = self._db.connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO clients (id, name) VALUES (?, ?)",
                (client.id, client.name),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, client_id: str) -> Optional[Client]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                "SELECT id, name FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
            return Client(id=row["id"], name=row["name"]) if row else None
        finally:
            conn.close()

    def list_all(self) -> list[Client]:
        conn = self._db.connect()
        try:
            rows = conn.execute("SELECT id, name FROM clients ORDER BY name").fetchall()
            return [Client(id=r["id"], name=r["name"]) for r in rows]
        finally:
            conn.close()


# ===================================================================
# Portfolio
# ===================================================================


class SqlitePortfolioRepository(PortfolioRepository):

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, portfolio: Portfolio) -> None:
        conn = self._db.connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO portfolios
                   (id, client_id, name, base_currency)
                   VALUES (?, ?, ?, ?)""",
                (portfolio.id, portfolio.client_id, portfolio.name, portfolio.base_currency),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, portfolio_id: str) -> Optional[Portfolio]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                "SELECT id, client_id, name, base_currency FROM portfolios WHERE id = ?",
                (portfolio_id,),
            ).fetchone()
            if not row:
                return None
            return Portfolio(
                id=row["id"],
                client_id=row["client_id"],
                name=row["name"],
                base_currency=row["base_currency"],
            )
        finally:
            conn.close()

    def list_by_client(self, client_id: str) -> list[Portfolio]:
        conn = self._db.connect()
        try:
            rows = conn.execute(
                "SELECT id, client_id, name, base_currency FROM portfolios WHERE client_id = ?",
                (client_id,),
            ).fetchall()
            return [
                Portfolio(id=r["id"], client_id=r["client_id"], name=r["name"], base_currency=r["base_currency"])
                for r in rows
            ]
        finally:
            conn.close()


# ===================================================================
# Instrument
# ===================================================================


class SqliteInstrumentRepository(InstrumentRepository):

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, instrument: Instrument) -> None:
        conn = self._db.connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO instruments (id, name, type, currency, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    instrument.id,
                    instrument.name,
                    instrument.type.value,
                    instrument.currency,
                    json.dumps(instrument.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, instrument_id: str) -> Optional[Instrument]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                "SELECT id, name, type, currency, metadata FROM instruments WHERE id = ?",
                (instrument_id,),
            ).fetchone()
            if not row:
                return None
            return Instrument(
                id=row["id"],
                name=row["name"],
                type=InstrumentType(row["type"]),
                currency=row["currency"],
                metadata=json.loads(row["metadata"] or "{}"),
            )
        finally:
            conn.close()

    def list_all(self) -> list[Instrument]:
        conn = self._db.connect()
        try:
            rows = conn.execute(
                "SELECT id, name, type, currency, metadata FROM instruments ORDER BY name"
            ).fetchall()
            return [
                Instrument(
                    id=r["id"],
                    name=r["name"],
                    type=InstrumentType(r["type"]),
                    currency=r["currency"],
                    metadata=json.loads(r["metadata"] or "{}"),
                )
                for r in rows
            ]
        finally:
            conn.close()

    def save_attribute(self, attr: InstrumentAttributeHistory) -> None:
        conn = self._db.connect()
        try:
            conn.execute(
                """INSERT INTO instrument_attributes_history
                   (instrument_id, attribute_name, attribute_value, valid_from, valid_to)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    attr.instrument_id,
                    attr.attribute_name,
                    attr.attribute_value,
                    _to_iso(attr.valid_from),
                    _to_iso(attr.valid_to) if attr.valid_to else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_attribute(
        self, instrument_id: str, attribute_name: str, as_of: datetime
    ) -> Optional[str]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                """SELECT attribute_value FROM instrument_attributes_history
                   WHERE instrument_id = ?
                     AND attribute_name = ?
                     AND valid_from <= ?
                     AND (valid_to IS NULL OR valid_to > ?)
                   ORDER BY valid_from DESC LIMIT 1""",
                (instrument_id, attribute_name, _to_iso(as_of), _to_iso(as_of)),
            ).fetchone()
            return row["attribute_value"] if row else None
        finally:
            conn.close()


# ===================================================================
# Cash Account
# ===================================================================


class SqliteCashAccountRepository(CashAccountRepository):

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, account: CashAccount) -> None:
        conn = self._db.connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO cash_accounts (id, portfolio_id, currency)
                   VALUES (?, ?, ?)""",
                (account.id, account.portfolio_id, account.currency),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, account_id: str) -> Optional[CashAccount]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                "SELECT id, portfolio_id, currency FROM cash_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if not row:
                return None
            return CashAccount(id=row["id"], portfolio_id=row["portfolio_id"], currency=row["currency"])
        finally:
            conn.close()

    def list_by_portfolio(self, portfolio_id: str) -> list[CashAccount]:
        conn = self._db.connect()
        try:
            rows = conn.execute(
                "SELECT id, portfolio_id, currency FROM cash_accounts WHERE portfolio_id = ?",
                (portfolio_id,),
            ).fetchall()
            return [
                CashAccount(id=r["id"], portfolio_id=r["portfolio_id"], currency=r["currency"])
                for r in rows
            ]
        finally:
            conn.close()

    def find_by_portfolio_and_currency(
        self, portfolio_id: str, currency: str
    ) -> Optional[CashAccount]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                "SELECT id, portfolio_id, currency FROM cash_accounts WHERE portfolio_id = ? AND currency = ?",
                (portfolio_id, currency),
            ).fetchone()
            if not row:
                return None
            return CashAccount(id=row["id"], portfolio_id=row["portfolio_id"], currency=row["currency"])
        finally:
            conn.close()


# ===================================================================
# Transaction
# ===================================================================


class SqliteTransactionRepository(TransactionRepository):

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, transaction: Transaction) -> None:
        conn = self._db.connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO transactions
                   (id, portfolio_id, instrument_id, type, quantity, price,
                    amount, currency, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    transaction.id,
                    transaction.portfolio_id,
                    transaction.instrument_id,
                    transaction.type.value,
                    transaction.quantity,
                    transaction.price,
                    transaction.amount,
                    transaction.currency,
                    _to_iso(transaction.timestamp),
                    json.dumps(transaction.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, transaction_id: str) -> Optional[Transaction]:
        conn = self._db.connect()
        try:
            row = conn.execute(
                """SELECT id, portfolio_id, instrument_id, type, quantity, price,
                          amount, currency, timestamp, metadata
                   FROM transactions WHERE id = ?""",
                (transaction_id,),
            ).fetchone()
            return self._row_to_tx(row) if row else None
        finally:
            conn.close()

    def list_by_portfolio(
        self, portfolio_id: str, up_to: Optional[datetime] = None
    ) -> list[Transaction]:
        conn = self._db.connect()
        try:
            if up_to:
                rows = conn.execute(
                    """SELECT id, portfolio_id, instrument_id, type, quantity, price,
                              amount, currency, timestamp, metadata
                       FROM transactions
                       WHERE portfolio_id = ? AND timestamp <= ?
                       ORDER BY timestamp""",
                    (portfolio_id, _to_iso(up_to)),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, portfolio_id, instrument_id, type, quantity, price,
                              amount, currency, timestamp, metadata
                       FROM transactions
                       WHERE portfolio_id = ?
                       ORDER BY timestamp""",
                    (portfolio_id,),
                ).fetchall()
            return [self._row_to_tx(r) for r in rows]
        finally:
            conn.close()

    def list_by_instrument(
        self, instrument_id: str, up_to: Optional[datetime] = None
    ) -> list[Transaction]:
        conn = self._db.connect()
        try:
            if up_to:
                rows = conn.execute(
                    """SELECT id, portfolio_id, instrument_id, type, quantity, price,
                              amount, currency, timestamp, metadata
                       FROM transactions
                       WHERE instrument_id = ? AND timestamp <= ?
                       ORDER BY timestamp""",
                    (instrument_id, _to_iso(up_to)),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, portfolio_id, instrument_id, type, quantity, price,
                              amount, currency, timestamp, metadata
                       FROM transactions
                       WHERE instrument_id = ?
                       ORDER BY timestamp""",
                    (instrument_id,),
                ).fetchall()
            return [self._row_to_tx(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _row_to_tx(row: dict) -> Transaction:
        return Transaction(
            id=row["id"],
            portfolio_id=row["portfolio_id"],
            instrument_id=row["instrument_id"],
            type=TransactionType(row["type"]),
            quantity=row["quantity"],
            price=row["price"],
            amount=row["amount"],
            currency=row["currency"],
            timestamp=_from_iso(row["timestamp"]),
            metadata=json.loads(row["metadata"] or "{}"),
        )
