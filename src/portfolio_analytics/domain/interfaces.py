"""
Abstract service interfaces.

These ABCs define the contracts that concrete services must implement.
Using abstract interfaces enables:
    • Swapping mock services for real ones (e.g., live pricing feeds).
    • Clean dependency injection in the application layer.
    • Testability via stubs and fakes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional

from portfolio_analytics.domain.enums import AllocationDimension
from portfolio_analytics.domain.models import (
    AllocationEntry,
    AttributionReport,
    BondAnalyticsReport,
    DataQualityReport,
    Holding,
    PerformanceReport,
    PortfolioOverview,
    RiskMetricsReport,
    Transaction,
)


class PricingServiceBase(ABC):
    """Provides instrument prices (spot or historical)."""

    @abstractmethod
    def get_price(self, instrument_id: str, on_date: date) -> float:
        """Return the price of *instrument_id* on *on_date*."""

    @abstractmethod
    def get_price_series(
        self, instrument_id: str, start: date, end: date
    ) -> list[tuple[date, float]]:
        """Return a list of ``(date, price)`` tuples over the given range."""


class FXServiceBase(ABC):
    """Provides foreign-exchange rates."""

    @abstractmethod
    def get_fx_rate(self, from_ccy: str, to_ccy: str, on_date: date) -> float:
        """
        Return the exchange rate to convert 1 unit of *from_ccy* into
        *to_ccy* on *on_date*.
        """


class TransactionServiceBase(ABC):
    """Executes trades and other cash/security movements."""

    @abstractmethod
    def execute_buy(
        self,
        portfolio_id: str,
        instrument_id: str,
        quantity: float,
        price: float,
        timestamp: datetime,
    ) -> Transaction:
        """Execute a buy order: increase position, decrease cash."""

    @abstractmethod
    def execute_sell(
        self,
        portfolio_id: str,
        instrument_id: str,
        quantity: float,
        price: float,
        timestamp: datetime,
    ) -> Transaction:
        """Execute a sell order: decrease position, increase cash."""

    @abstractmethod
    def execute_fx(
        self,
        portfolio_id: str,
        from_currency: str,
        to_currency: str,
        amount: float,
        rate: float,
        timestamp: datetime,
    ) -> tuple[Transaction, Transaction]:
        """Execute an FX conversion: debit one cash account, credit another."""


class PortfolioAnalyticsServiceBase(ABC):
    """Computes portfolio-level analytics from the transaction ledger."""

    @abstractmethod
    def get_holdings(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> list[Holding]:
        """Reconstruct positions from transactions up to *as_of*."""

    @abstractmethod
    def get_portfolio_value(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> float:
        """Total portfolio market value in base currency."""

    @abstractmethod
    def get_allocation(
        self,
        portfolio_id: str,
        by: AllocationDimension = AllocationDimension.ASSET_CLASS,
        as_of: Optional[datetime] = None,
    ) -> list[AllocationEntry]:
        """Return allocation breakdown by the chosen dimension."""

    @abstractmethod
    def get_unrealized_pnl(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> float:
        """Unrealised profit/loss (market value minus cost basis)."""

    @abstractmethod
    def get_overview(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> PortfolioOverview:
        """Full portfolio snapshot combining holdings, value, and P&L."""

    @abstractmethod
    def get_bond_analytics(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> BondAnalyticsReport:
        """Bond-specific clean/dirty price, accrual, and yield metrics."""

    @abstractmethod
    def get_performance_report(
        self,
        portfolio_id: str,
        as_of: Optional[datetime] = None,
        lookback_days: int = 252,
    ) -> PerformanceReport:
        """Portfolio-level performance report over a lookback window."""

    @abstractmethod
    def get_risk_metrics(
        self,
        portfolio_id: str,
        as_of: Optional[datetime] = None,
        lookback_days: int = 252,
    ) -> RiskMetricsReport:
        """Portfolio-level risk metrics derived from historical returns."""

    @abstractmethod
    def get_attribution_report(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> AttributionReport:
        """Contribution and attribution report by instrument and asset class."""

    @abstractmethod
    def get_data_quality_report(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> DataQualityReport:
        """Data completeness and freshness report for portfolio instruments."""
