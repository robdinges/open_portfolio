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


@dataclass
class BondAnalyticsEntry:
    """Bond-specific analytics for a single holding."""

    instrument_id: str
    instrument_name: str
    quantity: float
    currency: str
    clean_price: float
    dirty_price: float
    accrued_interest: float
    coupon_rate: float
    current_yield: float
    simplified_ytm: float
    macaulay_duration: float
    modified_duration: float
    convexity: float
    maturity_date: Optional[datetime]
    market_value: float


@dataclass
class BondAnalyticsReport:
    """Portfolio-level bond analytics summary."""

    portfolio_id: str
    currency: str
    as_of: datetime
    entries: list[BondAnalyticsEntry]
    total_accrued_interest: float
    total_dirty_value: float
    average_ytm: float


@dataclass
class PerformancePoint:
    """One point in a portfolio value time series."""

    timestamp: datetime
    portfolio_value: float


@dataclass
class HoldingPerformance:
    """Performance summary for one holding over a lookback period."""

    instrument_id: str
    instrument_name: str
    instrument_type: InstrumentType
    start_price: float
    end_price: float
    total_return: float
    annualized_return: float
    weight: float
    pnl_contribution: float


@dataclass
class PerformanceReport:
    """Portfolio performance metrics and time series."""

    portfolio_id: str
    currency: str
    as_of: datetime
    start_date: datetime
    total_return: float
    annualized_return: float
    money_weighted_return: float
    time_weighted_return: float
    max_drawdown: float
    series: list[PerformancePoint]
    holdings: list[HoldingPerformance]


@dataclass
class RiskMetricsReport:
    """Portfolio risk metrics derived from the return series."""

    portfolio_id: str
    currency: str
    as_of: datetime
    daily_volatility: float
    annualized_volatility: float
    sharpe_ratio: float
    var_95: float
    cvar_95: float
    max_drawdown: float
    concentration_index: float
    correlation_matrix: dict[str, dict[str, float]]


@dataclass
class AttributionEntry:
    """Attribution slice by instrument or aggregate grouping."""

    label: str
    market_value: float
    weight: float
    unrealized_pnl: float
    pnl_contribution: float


@dataclass
class AttributionReport:
    """Contribution and attribution report."""

    portfolio_id: str
    currency: str
    as_of: datetime
    by_instrument: list[AttributionEntry]
    by_asset_class: list[AttributionEntry]


@dataclass
class DataQualityIssue:
    """One data-quality finding for an instrument or portfolio."""

    instrument_id: str
    instrument_name: str
    severity: str
    field_name: str
    message: str


@dataclass
class DataQualityReport:
    """Coverage and quality checks for a portfolio's instrument data."""

    portfolio_id: str
    as_of: datetime
    coverage_pct: float
    issues: list[DataQualityIssue]
