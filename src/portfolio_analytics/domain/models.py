"""
Pure domain models — the canonical representation of business entities.

Rules:
    • Models are plain Python dataclasses with type hints.
    • No database, ORM, or I/O logic lives here.
    • All monetary amounts are stored as ``float`` (sufficient for MVP).
    • ``metadata`` dictionaries carry flexible JSONB-style attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from portfolio_analytics.domain.enums import InstrumentType, TransactionType


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


@dataclass
class Instrument:
    """A tradeable financial instrument (stock or bond)."""

    id: str
    name: str
    type: InstrumentType
    currency: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Portfolio:
    """An investment portfolio with a single base (reporting) currency."""

    id: str
    name: str
    client_id: str
    base_currency: str = "EUR"


@dataclass
class CashAccount:
    """
    A cash account linked to a portfolio in a specific currency.

    Balance is **derived** by summing all transactions that affect this
    account — no mutable ``balance`` field is stored.
    """

    id: str
    portfolio_id: str
    currency: str


@dataclass
class Transaction:
    """
    An immutable ledger entry describing a single financial event.

    For BUY/SELL: ``instrument_id`` is set, ``quantity`` and ``price`` define
    the trade, and ``amount`` equals ``quantity × price`` (cash impact).

    For FX: two paired transactions (one debit, one credit) share the same
    ``metadata["fx_pair_id"]``.

    For FEE / INTEREST: ``instrument_id`` may be ``None``; the ``amount``
    captures the fee or coupon.
    """

    id: str
    portfolio_id: str
    instrument_id: Optional[str]
    type: TransactionType
    quantity: float
    price: float
    amount: float
    currency: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class Client:
    """A client who owns one or more portfolios."""

    id: str
    name: str


# ---------------------------------------------------------------------------
# Attribute history (temporal dimension)
# ---------------------------------------------------------------------------


@dataclass
class InstrumentAttributeHistory:
    """
    A time-bounded attribute for an instrument.

    Enables historical reconstruction: resolve the attribute whose period
    satisfies ``valid_from <= query_date < valid_to``.
    """

    instrument_id: str
    attribute_name: str
    attribute_value: str
    valid_from: datetime
    valid_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Derived / read-only value objects returned by analytics
# ---------------------------------------------------------------------------


@dataclass
class Holding:
    """A position in a single instrument at a point in time."""

    instrument_id: str
    instrument_name: str
    instrument_type: InstrumentType
    quantity: float
    average_cost: float
    market_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    allocation_pct: float
    currency: str


@dataclass
class AllocationEntry:
    """One slice of an allocation breakdown (by asset class or currency)."""

    label: str
    market_value: float
    weight: float  # 0.0 – 1.0


@dataclass
class PortfolioOverview:
    """Aggregate snapshot returned by the analytics service."""

    portfolio_id: str
    portfolio_value: float
    currency: str
    holdings: list[Holding]
    cash_balances: dict[str, float]  # currency → balance
    unrealized_pnl: float
    as_of: datetime
