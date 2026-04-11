"""
Portfolio analytics service — computes holdings, value, allocation, and P&L.

Core invariant: **all analytics are reconstructed from the transaction ledger**
at a given point in time. No snapshots are used.

Average cost method
-------------------
For each BUY the cost basis increases:
    total_cost += quantity × price × fx_to_base
For each SELL the cost basis decreases proportionally:
    total_cost -= quantity × average_cost

All monetary values returned by this service are expressed in the
portfolio's **base currency**.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from portfolio_analytics.domain.enums import (
    AllocationDimension,
    InstrumentType,
    TransactionType,
)
from portfolio_analytics.domain.interfaces import (
    FXServiceBase,
    PortfolioAnalyticsServiceBase,
    PricingServiceBase,
)
from portfolio_analytics.domain.models import (
    AllocationEntry,
    Holding,
    PortfolioOverview,
    Transaction,
)
from portfolio_analytics.repositories.base import (
    CashAccountRepository,
    InstrumentRepository,
    PortfolioRepository,
    TransactionRepository,
)


class PortfolioAnalyticsService(PortfolioAnalyticsServiceBase):
    """Concrete analytics engine over SQLite repositories + mock services."""

    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        instrument_repo: InstrumentRepository,
        transaction_repo: TransactionRepository,
        cash_account_repo: CashAccountRepository,
        pricing_service: PricingServiceBase,
        fx_service: FXServiceBase,
    ) -> None:
        self._portfolios = portfolio_repo
        self._instruments = instrument_repo
        self._transactions = transaction_repo
        self._cash_accounts = cash_account_repo
        self._pricing = pricing_service
        self._fx = fx_service

    # ------------------------------------------------------------------
    # Holdings
    # ------------------------------------------------------------------

    def get_holdings(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> list[Holding]:
        as_of = as_of or datetime.now()
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio not found: {portfolio_id}")

        txs = self._transactions.list_by_portfolio(portfolio_id, up_to=as_of)

        # Build positions: instrument_id → {quantity, total_cost_base}
        positions: dict[str, dict] = {}
        for tx in txs:
            if tx.instrument_id is None:
                continue
            if tx.type not in (TransactionType.BUY, TransactionType.SELL):
                continue

            pos = positions.setdefault(
                tx.instrument_id, {"quantity": 0.0, "total_cost": 0.0}
            )
            instrument = self._instruments.get(tx.instrument_id)
            if instrument is None:
                continue

            fx_to_base = self._fx.get_fx_rate(
                instrument.currency, portfolio.base_currency, tx.timestamp.date()
            )

            if tx.type == TransactionType.BUY:
                cost = tx.quantity * tx.price * fx_to_base
                pos["quantity"] += tx.quantity
                pos["total_cost"] += cost
            elif tx.type == TransactionType.SELL:
                if pos["quantity"] > 0:
                    avg = pos["total_cost"] / pos["quantity"]
                    pos["total_cost"] -= tx.quantity * avg
                pos["quantity"] -= tx.quantity

        # Convert positions to Holding objects with current market values
        holdings: list[Holding] = []
        for instr_id, pos in positions.items():
            if pos["quantity"] <= 0:
                continue
            instrument = self._instruments.get(instr_id)
            if instrument is None:
                continue

            market_price = self._pricing.get_price(instr_id, as_of.date())
            fx_to_base = self._fx.get_fx_rate(
                instrument.currency, portfolio.base_currency, as_of.date()
            )
            market_value = pos["quantity"] * market_price * fx_to_base
            cost_basis = pos["total_cost"]
            avg_cost = cost_basis / pos["quantity"] if pos["quantity"] else 0.0

            holdings.append(
                Holding(
                    instrument_id=instr_id,
                    instrument_name=instrument.name,
                    instrument_type=instrument.type,
                    quantity=pos["quantity"],
                    average_cost=round(avg_cost, 4),
                    market_price=round(market_price, 4),
                    market_value=round(market_value, 2),
                    cost_basis=round(cost_basis, 2),
                    unrealized_pnl=round(market_value - cost_basis, 2),
                    allocation_pct=0.0,  # filled below
                    currency=instrument.currency,
                )
            )

        # Compute allocation percentages
        total_value = sum(h.market_value for h in holdings)
        if total_value > 0:
            for h in holdings:
                h.allocation_pct = round(h.market_value / total_value, 4)

        return holdings

    # ------------------------------------------------------------------
    # Portfolio value
    # ------------------------------------------------------------------

    def get_portfolio_value(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> float:
        as_of = as_of or datetime.now()
        holdings = self.get_holdings(portfolio_id, as_of)
        securities_value = sum(h.market_value for h in holdings)
        cash_value = self._total_cash_in_base(portfolio_id, as_of)
        return round(securities_value + cash_value, 2)

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def get_allocation(
        self,
        portfolio_id: str,
        by: AllocationDimension = AllocationDimension.ASSET_CLASS,
        as_of: Optional[datetime] = None,
    ) -> list[AllocationEntry]:
        holdings = self.get_holdings(portfolio_id, as_of)
        total = sum(h.market_value for h in holdings)
        if total == 0:
            return []

        buckets: dict[str, float] = {}
        for h in holdings:
            if by == AllocationDimension.ASSET_CLASS:
                key = h.instrument_type.value
            elif by == AllocationDimension.CURRENCY:
                key = h.currency
            else:
                key = h.instrument_name
            buckets[key] = buckets.get(key, 0.0) + h.market_value

        return [
            AllocationEntry(
                label=label,
                market_value=round(value, 2),
                weight=round(value / total, 4),
            )
            for label, value in sorted(buckets.items(), key=lambda x: -x[1])
        ]

    # ------------------------------------------------------------------
    # Unrealised P&L
    # ------------------------------------------------------------------

    def get_unrealized_pnl(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> float:
        holdings = self.get_holdings(portfolio_id, as_of)
        return round(sum(h.unrealized_pnl for h in holdings), 2)

    # ------------------------------------------------------------------
    # Full overview
    # ------------------------------------------------------------------

    def get_overview(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> PortfolioOverview:
        as_of = as_of or datetime.now()
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio not found: {portfolio_id}")

        holdings = self.get_holdings(portfolio_id, as_of)
        cash_balances = self._cash_balances(portfolio_id, as_of)
        securities_value = sum(h.market_value for h in holdings)
        cash_in_base = self._total_cash_in_base(portfolio_id, as_of)
        total_value = securities_value + cash_in_base

        return PortfolioOverview(
            portfolio_id=portfolio_id,
            portfolio_value=round(total_value, 2),
            currency=portfolio.base_currency,
            holdings=holdings,
            cash_balances=cash_balances,
            unrealized_pnl=round(sum(h.unrealized_pnl for h in holdings), 2),
            as_of=as_of,
        )

    # ------------------------------------------------------------------
    # Cash helpers
    # ------------------------------------------------------------------

    def _cash_balances(
        self, portfolio_id: str, as_of: datetime
    ) -> dict[str, float]:
        accounts = self._cash_accounts.list_by_portfolio(portfolio_id)
        txs = self._transactions.list_by_portfolio(portfolio_id, up_to=as_of)
        balances: dict[str, float] = {a.currency: 0.0 for a in accounts}
        for tx in txs:
            if tx.currency in balances:
                balances[tx.currency] += tx.amount
        return {ccy: round(bal, 2) for ccy, bal in balances.items()}

    def _total_cash_in_base(self, portfolio_id: str, as_of: datetime) -> float:
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio is None:
            return 0.0
        balances = self._cash_balances(portfolio_id, as_of)
        total = 0.0
        for ccy, bal in balances.items():
            fx = self._fx.get_fx_rate(ccy, portfolio.base_currency, as_of.date())
            total += bal * fx
        return total
