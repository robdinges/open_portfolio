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

from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

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
    AttributionEntry,
    AttributionReport,
    BondAnalyticsEntry,
    BondAnalyticsReport,
    DataQualityIssue,
    DataQualityReport,
    Holding,
    HoldingPerformance,
    PerformancePoint,
    PerformanceReport,
    PortfolioOverview,
    RiskMetricsReport,
)
from portfolio_analytics.repositories.base import (
    CashAccountRepository,
    InstrumentRepository,
    PortfolioRepository,
    TransactionRepository,
)
from portfolio_analytics.utils.bond_math import (
    accrued_interest,
    convexity,
    macaulay_duration,
    modified_duration,
    solve_ytm_from_clean_price,
    xirr,
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

    def get_bond_analytics(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> BondAnalyticsReport:
        as_of = as_of or datetime.now()
        portfolio = self._require_portfolio(portfolio_id)
        holdings = [
            holding
            for holding in self.get_holdings(portfolio_id, as_of)
            if holding.instrument_type == InstrumentType.BOND
        ]

        entries: list[BondAnalyticsEntry] = []
        total_accrued_base = 0.0
        total_dirty_value = 0.0

        for holding in holdings:
            instrument = self._require_instrument(holding.instrument_id)
            metadata = instrument.metadata
            coupon_rate = float(metadata.get("coupon_rate", 0.0))
            face_value = float(metadata.get("face_value", 100.0))
            payment_frequency = int(metadata.get("payment_frequency", 2))
            day_count = str(metadata.get("day_count_convention", "ACT/ACT"))
            maturity_date = self._coerce_datetime(
                metadata.get("maturity_date")
                or f"{int(metadata.get('maturity_year', as_of.year))}-12-31"
            )

            accrued_per_100 = accrued_interest(
                settlement=as_of.date(),
                maturity=maturity_date.date(),
                coupon_rate_pct=coupon_rate,
                face_value=face_value,
                frequency=payment_frequency,
                convention=day_count,
            )
            dirty_price = holding.market_price + accrued_per_100
            ytm = solve_ytm_from_clean_price(
                settlement=as_of.date(),
                maturity=maturity_date.date(),
                clean_price_pct=holding.market_price,
                coupon_rate_pct=coupon_rate,
                frequency=payment_frequency,
                face_value=face_value,
                convention=day_count,
            )
            mac_duration = macaulay_duration(
                settlement=as_of.date(),
                maturity=maturity_date.date(),
                coupon_rate_pct=coupon_rate,
                ytm=ytm,
                frequency=payment_frequency,
                face_value=face_value,
            )
            mod_duration = modified_duration(mac_duration, ytm, payment_frequency)
            cx = convexity(
                settlement=as_of.date(),
                maturity=maturity_date.date(),
                coupon_rate_pct=coupon_rate,
                ytm=ytm,
                frequency=payment_frequency,
                face_value=face_value,
            )
            fx_to_base = self._fx.get_fx_rate(
                instrument.currency, portfolio.base_currency, as_of.date()
            )
            accrued_total_native = (holding.quantity / face_value) * accrued_per_100
            accrued_total_base = accrued_total_native * fx_to_base
            dirty_market_value = holding.market_value + accrued_total_base
            total_accrued_base += accrued_total_base
            total_dirty_value += dirty_market_value

            entries.append(
                BondAnalyticsEntry(
                    instrument_id=holding.instrument_id,
                    instrument_name=holding.instrument_name,
                    quantity=holding.quantity,
                    currency=holding.currency,
                    clean_price=round(holding.market_price, 4),
                    dirty_price=round(dirty_price, 4),
                    accrued_interest=round(accrued_total_native, 2),
                    coupon_rate=round(coupon_rate, 4),
                    current_yield=round((coupon_rate / holding.market_price) if holding.market_price else 0.0, 4),
                    simplified_ytm=round(ytm, 4),
                    macaulay_duration=round(mac_duration, 4),
                    modified_duration=round(mod_duration, 4),
                    convexity=round(cx, 4),
                    maturity_date=maturity_date,
                    market_value=round(dirty_market_value, 2),
                )
            )

        average_ytm = 0.0
        if entries:
            average_ytm = sum(entry.simplified_ytm for entry in entries) / len(entries)

        return BondAnalyticsReport(
            portfolio_id=portfolio_id,
            currency=portfolio.base_currency,
            as_of=as_of,
            entries=entries,
            total_accrued_interest=round(total_accrued_base, 2),
            total_dirty_value=round(total_dirty_value, 2),
            average_ytm=round(average_ytm, 4),
        )

    def get_performance_report(
        self,
        portfolio_id: str,
        as_of: Optional[datetime] = None,
        lookback_days: int = 252,
    ) -> PerformanceReport:
        as_of = as_of or datetime.now()
        portfolio = self._require_portfolio(portfolio_id)
        start_date = as_of - timedelta(days=lookback_days)
        series = self._portfolio_value_series(portfolio_id, start_date, as_of)
        values = np.array([point.portfolio_value for point in series], dtype=float)
        start_value = float(values[0]) if len(values) else 0.0
        end_value = float(values[-1]) if len(values) else 0.0
        total_return = ((end_value / start_value) - 1) if start_value > 0 else 0.0
        elapsed_days = max((as_of - start_date).days, 1)
        annualized_return = ((1 + total_return) ** (365 / elapsed_days) - 1) if start_value > 0 else 0.0
        flow_series = self._external_cash_flows_by_day(portfolio_id, start_date, as_of)
        time_weighted_return = self._time_weighted_return(series, flow_series)
        money_weighted_return = self._money_weighted_return(portfolio_id, start_date, as_of, start_value, end_value)
        max_drawdown = self._max_drawdown(values)

        overview = self.get_overview(portfolio_id, as_of)
        holdings_performance: list[HoldingPerformance] = []
        denominator = end_value if end_value > 0 else 1.0
        for holding in overview.holdings:
            start_price = self._pricing.get_price(holding.instrument_id, start_date.date())
            end_price = self._pricing.get_price(holding.instrument_id, as_of.date())
            instrument_return = ((end_price / start_price) - 1) if start_price > 0 else 0.0
            instrument_annualized = (
                (1 + instrument_return) ** (365 / elapsed_days) - 1
                if start_price > 0
                else 0.0
            )
            holdings_performance.append(
                HoldingPerformance(
                    instrument_id=holding.instrument_id,
                    instrument_name=holding.instrument_name,
                    instrument_type=holding.instrument_type,
                    start_price=round(start_price, 4),
                    end_price=round(end_price, 4),
                    total_return=round(instrument_return, 4),
                    annualized_return=round(instrument_annualized, 4),
                    weight=round(holding.market_value / denominator, 4),
                    pnl_contribution=round(holding.unrealized_pnl / denominator, 4),
                )
            )

        return PerformanceReport(
            portfolio_id=portfolio_id,
            currency=portfolio.base_currency,
            as_of=as_of,
            start_date=start_date,
            total_return=round(total_return, 4),
            annualized_return=round(annualized_return, 4),
            money_weighted_return=round(money_weighted_return, 4),
            time_weighted_return=round(time_weighted_return, 4),
            max_drawdown=round(max_drawdown, 4),
            series=series,
            holdings=holdings_performance,
        )

    def get_risk_metrics(
        self,
        portfolio_id: str,
        as_of: Optional[datetime] = None,
        lookback_days: int = 252,
    ) -> RiskMetricsReport:
        as_of = as_of or datetime.now()
        portfolio = self._require_portfolio(portfolio_id)
        performance = self.get_performance_report(portfolio_id, as_of, lookback_days)
        values = np.array([point.portfolio_value for point in performance.series], dtype=float)
        returns = pd.Series(values).pct_change().dropna()
        mean_return = float(returns.mean()) if not returns.empty else 0.0
        daily_vol = float(returns.std(ddof=0)) if not returns.empty else 0.0
        annual_vol = daily_vol * np.sqrt(252)
        risk_free_daily = 0.02 / 252
        sharpe = ((mean_return - risk_free_daily) / daily_vol * np.sqrt(252)) if daily_vol > 0 else 0.0
        var_cutoff = float(np.percentile(returns, 5)) if not returns.empty else 0.0
        tail = returns[returns <= var_cutoff]
        cvar = float(tail.mean()) if not tail.empty else 0.0
        holdings = self.get_holdings(portfolio_id, as_of)
        concentration = sum(holding.allocation_pct ** 2 for holding in holdings)
        correlation_matrix = self._correlation_matrix(portfolio_id, as_of, lookback_days)

        return RiskMetricsReport(
            portfolio_id=portfolio_id,
            currency=portfolio.base_currency,
            as_of=as_of,
            daily_volatility=round(daily_vol, 6),
            annualized_volatility=round(annual_vol, 6),
            sharpe_ratio=round(sharpe, 4),
            var_95=round(-var_cutoff, 4),
            cvar_95=round(-cvar, 4),
            max_drawdown=round(performance.max_drawdown, 4),
            concentration_index=round(concentration, 4),
            correlation_matrix=correlation_matrix,
        )

    def get_attribution_report(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> AttributionReport:
        as_of = as_of or datetime.now()
        portfolio = self._require_portfolio(portfolio_id)
        holdings = self.get_holdings(portfolio_id, as_of)
        portfolio_value = self.get_portfolio_value(portfolio_id, as_of)
        denominator = portfolio_value if portfolio_value > 0 else 1.0

        by_instrument = [
            AttributionEntry(
                label=holding.instrument_name,
                market_value=round(holding.market_value, 2),
                weight=round(holding.market_value / denominator, 4),
                unrealized_pnl=round(holding.unrealized_pnl, 2),
                pnl_contribution=round(holding.unrealized_pnl / denominator, 4),
            )
            for holding in sorted(holdings, key=lambda item: item.market_value, reverse=True)
        ]

        grouped: dict[str, dict[str, float]] = {}
        for holding in holdings:
            label = holding.instrument_type.value
            bucket = grouped.setdefault(label, {"market_value": 0.0, "unrealized_pnl": 0.0})
            bucket["market_value"] += holding.market_value
            bucket["unrealized_pnl"] += holding.unrealized_pnl
        by_asset_class = [
            AttributionEntry(
                label=label,
                market_value=round(values["market_value"], 2),
                weight=round(values["market_value"] / denominator, 4),
                unrealized_pnl=round(values["unrealized_pnl"], 2),
                pnl_contribution=round(values["unrealized_pnl"] / denominator, 4),
            )
            for label, values in sorted(grouped.items(), key=lambda item: -item[1]["market_value"])
        ]

        return AttributionReport(
            portfolio_id=portfolio_id,
            currency=portfolio.base_currency,
            as_of=as_of,
            by_instrument=by_instrument,
            by_asset_class=by_asset_class,
        )

    def get_data_quality_report(
        self, portfolio_id: str, as_of: Optional[datetime] = None
    ) -> DataQualityReport:
        as_of = as_of or datetime.now()
        holdings = self.get_holdings(portfolio_id, as_of)
        issues: list[DataQualityIssue] = []
        checks = 0
        passed = 0

        for holding in holdings:
            instrument = self._require_instrument(holding.instrument_id)
            metadata = instrument.metadata
            required_fields = ["sector", "country", "benchmark_id"]
            if instrument.type == InstrumentType.BOND:
                required_fields = [
                    "coupon_rate",
                    "payment_frequency",
                    "day_count_convention",
                    "face_value",
                    "issue_date",
                    "maturity_date",
                ]
            for field_name in required_fields:
                checks += 1
                if metadata.get(field_name) in (None, ""):
                    issues.append(
                        DataQualityIssue(
                            instrument_id=instrument.id,
                            instrument_name=instrument.name,
                            severity="warning",
                            field_name=field_name,
                            message=f"Missing metadata field: {field_name}",
                        )
                    )
                else:
                    passed += 1
            checks += 1
            try:
                self._pricing.get_price(instrument.id, as_of.date())
                passed += 1
            except ValueError:
                issues.append(
                    DataQualityIssue(
                        instrument_id=instrument.id,
                        instrument_name=instrument.name,
                        severity="critical",
                        field_name="price",
                        message="Missing price for selected as-of date",
                    )
                )

        coverage = (passed / checks * 100) if checks else 100.0
        return DataQualityReport(
            portfolio_id=portfolio_id,
            as_of=as_of,
            coverage_pct=round(coverage, 2),
            issues=issues,
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

    def _portfolio_value_series(
        self, portfolio_id: str, start: datetime, end: datetime
    ) -> list[PerformancePoint]:
        dates = pd.date_range(start=start.date(), end=end.date(), freq="B")
        series: list[PerformancePoint] = []
        for ts in dates:
            point_date = datetime(ts.year, ts.month, ts.day, 23, 59, 59)
            series.append(
                PerformancePoint(
                    timestamp=point_date,
                    portfolio_value=self.get_portfolio_value(portfolio_id, point_date),
                )
            )
        if not series:
            series.append(PerformancePoint(timestamp=end, portfolio_value=self.get_portfolio_value(portfolio_id, end)))
        return series

    def _money_weighted_return(
        self,
        portfolio_id: str,
        start: datetime,
        end: datetime,
        start_value: float,
        end_value: float,
    ) -> float:
        dated_flows: list[tuple[date, float]] = [(start.date(), -start_value)]
        daily_flows = self._external_cash_flows_by_day(portfolio_id, start, end)
        for flow_date, flow_amount in sorted(daily_flows.items()):
            if flow_date == start.date() or flow_date == end.date():
                continue
            dated_flows.append((flow_date, -flow_amount))
        dated_flows.append((end.date(), end_value))
        if len(dated_flows) < 2:
            return 0.0
        irr = xirr(dated_flows)
        if irr is None or np.isnan(irr) or not np.isfinite(irr):
            return 0.0
        return float(irr)

    def _time_weighted_return(
        self,
        series: list[PerformancePoint],
        daily_external_flows: dict[date, float],
    ) -> float:
        if len(series) < 2:
            return 0.0
        subperiod_returns: list[float] = []
        for idx in range(1, len(series)):
            prev_value = series[idx - 1].portfolio_value
            if prev_value <= 0:
                continue
            current_date = series[idx].timestamp.date()
            external_flow = daily_external_flows.get(current_date, 0.0)
            period_return = (series[idx].portfolio_value - series[idx - 1].portfolio_value - external_flow) / prev_value
            subperiod_returns.append(period_return)
        if not subperiod_returns:
            return 0.0
        return float(np.prod([1 + r for r in subperiod_returns]) - 1)

    def _max_drawdown(self, values: np.ndarray) -> float:
        if values.size == 0:
            return 0.0
        running_max = np.maximum.accumulate(values)
        drawdowns = np.where(running_max > 0, (values / running_max) - 1, 0)
        return float(abs(drawdowns.min()))

    def _external_cash_flows_by_day(
        self, portfolio_id: str, start: datetime, end: datetime
    ) -> dict[date, float]:
        txs = self._transactions.list_by_portfolio(portfolio_id, up_to=end)
        flows: dict[date, float] = {}
        for tx in txs:
            if tx.timestamp < start or tx.timestamp > end:
                continue
            if tx.type == TransactionType.FX:
                continue
            if tx.instrument_id is not None:
                continue
            flow_day = tx.timestamp.date()
            flows[flow_day] = flows.get(flow_day, 0.0) + tx.amount
        return flows

    def _correlation_matrix(
        self, portfolio_id: str, as_of: datetime, lookback_days: int
    ) -> dict[str, dict[str, float]]:
        holdings = self.get_holdings(portfolio_id, as_of)
        if not holdings:
            return {}
        start = as_of - timedelta(days=lookback_days)
        frame = pd.DataFrame()
        for holding in holdings:
            series = self._pricing.get_price_series(holding.instrument_id, start.date(), as_of.date())
            if len(series) < 2:
                continue
            dates = [item[0] for item in series]
            prices = [item[1] for item in series]
            frame[holding.instrument_name] = pd.Series(prices, index=pd.to_datetime(dates))
        if frame.empty:
            return {}
        returns = frame.sort_index().pct_change().dropna(how="all")
        if returns.empty:
            return {}
        corr = returns.corr().fillna(1.0)
        return {
            row: {col: round(float(corr.loc[row, col]), 4) for col in corr.columns}
            for row in corr.index
        }

    def _require_portfolio(self, portfolio_id: str):
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio not found: {portfolio_id}")
        return portfolio

    def _require_instrument(self, instrument_id: str):
        instrument = self._instruments.get(instrument_id)
        if instrument is None:
            raise ValueError(f"Instrument not found: {instrument_id}")
        return instrument

    def _coerce_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError(f"Cannot parse datetime from {value!r}")
