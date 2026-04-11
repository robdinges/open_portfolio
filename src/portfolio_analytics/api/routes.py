"""
FastAPI route definitions.

Endpoints
---------
GET  /portfolio/{id}/overview?date=          Full portfolio snapshot.
GET  /portfolio/{id}/allocation?by=&date=    Allocation breakdown.
GET  /portfolio/{id}/transactions             Transaction ledger.
GET  /instrument/{id}                         Instrument detail.
GET  /pricing/{instrument_id}?date=           Spot price lookup.
GET  /health                                  Liveness probe.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from portfolio_analytics.api.schemas import (
    AllocationEntryResponse,
    AttributionEntryResponse,
    AttributionReportResponse,
    BondAnalyticsEntryResponse,
    BondAnalyticsReportResponse,
    DataQualityIssueResponse,
    DataQualityReportResponse,
    HoldingPerformanceResponse,
    InstrumentResponse,
    PerformancePointResponse,
    PerformanceReportResponse,
    PortfolioOverviewResponse,
    PriceResponse,
    RiskMetricsReportResponse,
    TransactionResponse,
)
from portfolio_analytics.domain.enums import AllocationDimension
from portfolio_analytics.domain.interfaces import (
    FXServiceBase,
    PortfolioAnalyticsServiceBase,
    PricingServiceBase,
)
from portfolio_analytics.repositories.base import (
    InstrumentRepository,
    TransactionRepository,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# These module-level references are set by ``app.dependencies.wire_routes``
# during application startup.  FastAPI's dependency-injection is intentionally
# kept simple here (module globals) — a future iteration can switch to
# FastAPI's ``Depends()`` with provider functions.
# ---------------------------------------------------------------------------
analytics_service: PortfolioAnalyticsServiceBase = None  # type: ignore[assignment]
pricing_service: PricingServiceBase = None  # type: ignore[assignment]
fx_service: FXServiceBase = None  # type: ignore[assignment]
instrument_repo: InstrumentRepository = None  # type: ignore[assignment]
transaction_repo: TransactionRepository = None  # type: ignore[assignment]


# ===================================================================
# Portfolio endpoints
# ===================================================================


@router.get(
    "/portfolio/{portfolio_id}/overview",
    response_model=PortfolioOverviewResponse,
    tags=["Portfolio"],
)
def portfolio_overview(
    portfolio_id: str,
    date: Optional[str] = Query(None, description="ISO date, e.g. 2025-06-15"),
):
    """Full portfolio snapshot: holdings, cash, value, P&L."""
    as_of = _parse_date(date)
    try:
        overview = analytics_service.get_overview(portfolio_id, as_of)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PortfolioOverviewResponse(
        portfolio_id=overview.portfolio_id,
        portfolio_value=overview.portfolio_value,
        currency=overview.currency,
        holdings=[
            _holding_to_response(h) for h in overview.holdings
        ],
        cash_balances=overview.cash_balances,
        unrealized_pnl=overview.unrealized_pnl,
        as_of=overview.as_of,
    )


@router.get(
    "/portfolio/{portfolio_id}/allocation",
    response_model=list[AllocationEntryResponse],
    tags=["Portfolio"],
)
def portfolio_allocation(
    portfolio_id: str,
    by: str = Query("asset_class", description="asset_class | currency | instrument"),
    date: Optional[str] = Query(None),
):
    """Allocation breakdown by asset class, currency, or instrument."""
    as_of = _parse_date(date)
    try:
        dimension = AllocationDimension(by)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dimension: {by}")
    try:
        entries = analytics_service.get_allocation(portfolio_id, dimension, as_of)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [
        AllocationEntryResponse(label=e.label, market_value=e.market_value, weight=e.weight)
        for e in entries
    ]


@router.get(
    "/portfolio/{portfolio_id}/transactions",
    response_model=list[TransactionResponse],
    tags=["Portfolio"],
)
def portfolio_transactions(portfolio_id: str):
    """Full transaction history for a portfolio."""
    txs = transaction_repo.list_by_portfolio(portfolio_id)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found")
    return [_tx_to_response(tx) for tx in txs]


@router.get(
    "/portfolio/{portfolio_id}/bond-analytics",
    response_model=BondAnalyticsReportResponse,
    tags=["Portfolio"],
)
def portfolio_bond_analytics(
    portfolio_id: str,
    date: Optional[str] = Query(None),
):
    as_of = _parse_date(date)
    try:
        report = analytics_service.get_bond_analytics(portfolio_id, as_of)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return BondAnalyticsReportResponse(
        portfolio_id=report.portfolio_id,
        currency=report.currency,
        as_of=report.as_of,
        entries=[
            BondAnalyticsEntryResponse(**entry.__dict__) for entry in report.entries
        ],
        total_accrued_interest=report.total_accrued_interest,
        total_dirty_value=report.total_dirty_value,
        average_ytm=report.average_ytm,
    )


@router.get(
    "/portfolio/{portfolio_id}/performance",
    response_model=PerformanceReportResponse,
    tags=["Portfolio"],
)
def portfolio_performance(
    portfolio_id: str,
    date: Optional[str] = Query(None),
    lookback_days: int = Query(252, ge=20, le=2000),
):
    as_of = _parse_date(date)
    try:
        report = analytics_service.get_performance_report(portfolio_id, as_of, lookback_days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PerformanceReportResponse(
        portfolio_id=report.portfolio_id,
        currency=report.currency,
        as_of=report.as_of,
        start_date=report.start_date,
        total_return=report.total_return,
        annualized_return=report.annualized_return,
        money_weighted_return=report.money_weighted_return,
        time_weighted_return=report.time_weighted_return,
        max_drawdown=report.max_drawdown,
        series=[PerformancePointResponse(**point.__dict__) for point in report.series],
        holdings=[
            HoldingPerformanceResponse(
                instrument_id=holding.instrument_id,
                instrument_name=holding.instrument_name,
                instrument_type=holding.instrument_type.value,
                start_price=holding.start_price,
                end_price=holding.end_price,
                total_return=holding.total_return,
                annualized_return=holding.annualized_return,
                weight=holding.weight,
                pnl_contribution=holding.pnl_contribution,
            )
            for holding in report.holdings
        ],
    )


@router.get(
    "/portfolio/{portfolio_id}/risk",
    response_model=RiskMetricsReportResponse,
    tags=["Portfolio"],
)
def portfolio_risk(
    portfolio_id: str,
    date: Optional[str] = Query(None),
    lookback_days: int = Query(252, ge=20, le=2000),
):
    as_of = _parse_date(date)
    try:
        report = analytics_service.get_risk_metrics(portfolio_id, as_of, lookback_days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return RiskMetricsReportResponse(**report.__dict__)


@router.get(
    "/portfolio/{portfolio_id}/attribution",
    response_model=AttributionReportResponse,
    tags=["Portfolio"],
)
def portfolio_attribution(
    portfolio_id: str,
    date: Optional[str] = Query(None),
):
    as_of = _parse_date(date)
    try:
        report = analytics_service.get_attribution_report(portfolio_id, as_of)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AttributionReportResponse(
        portfolio_id=report.portfolio_id,
        currency=report.currency,
        as_of=report.as_of,
        by_instrument=[AttributionEntryResponse(**entry.__dict__) for entry in report.by_instrument],
        by_asset_class=[AttributionEntryResponse(**entry.__dict__) for entry in report.by_asset_class],
    )


@router.get(
    "/portfolio/{portfolio_id}/data-quality",
    response_model=DataQualityReportResponse,
    tags=["Portfolio"],
)
def portfolio_data_quality(
    portfolio_id: str,
    date: Optional[str] = Query(None),
):
    as_of = _parse_date(date)
    try:
        report = analytics_service.get_data_quality_report(portfolio_id, as_of)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return DataQualityReportResponse(
        portfolio_id=report.portfolio_id,
        as_of=report.as_of,
        coverage_pct=report.coverage_pct,
        issues=[DataQualityIssueResponse(**issue.__dict__) for issue in report.issues],
    )


# ===================================================================
# Instrument endpoints
# ===================================================================


@router.get(
    "/instrument/{instrument_id}",
    response_model=InstrumentResponse,
    tags=["Instrument"],
)
def get_instrument(instrument_id: str):
    """Instrument detail including metadata."""
    inst = instrument_repo.get(instrument_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return InstrumentResponse(
        id=inst.id,
        name=inst.name,
        type=inst.type.value,
        currency=inst.currency,
        metadata=inst.metadata,
    )


@router.get(
    "/pricing/{instrument_id}",
    response_model=PriceResponse,
    tags=["Pricing"],
)
def get_price(
    instrument_id: str,
    date: Optional[str] = Query(None),
):
    """Spot price for an instrument on a given date."""
    on_date = (_parse_date(date) or datetime.now()).date()
    try:
        price = pricing_service.get_price(instrument_id, on_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PriceResponse(
        instrument_id=instrument_id,
        date=on_date.isoformat(),
        price=round(price, 4),
    )


# ===================================================================
# Health
# ===================================================================


@router.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


# ===================================================================
# Helpers
# ===================================================================


def _parse_date(iso_str: Optional[str]) -> Optional[datetime]:
    if iso_str is None:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        try:
            d = date.fromisoformat(iso_str)
            return datetime(d.year, d.month, d.day, 23, 59, 59)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date: {iso_str}")


def _holding_to_response(h):
    from portfolio_analytics.api.schemas import HoldingResponse

    return HoldingResponse(
        instrument_id=h.instrument_id,
        instrument_name=h.instrument_name,
        instrument_type=h.instrument_type.value,
        quantity=h.quantity,
        average_cost=h.average_cost,
        market_price=h.market_price,
        market_value=h.market_value,
        cost_basis=h.cost_basis,
        unrealized_pnl=h.unrealized_pnl,
        allocation_pct=h.allocation_pct,
        currency=h.currency,
    )


def _tx_to_response(tx):
    return TransactionResponse(
        id=tx.id,
        portfolio_id=tx.portfolio_id,
        instrument_id=tx.instrument_id,
        type=tx.type.value,
        quantity=tx.quantity,
        price=tx.price,
        amount=tx.amount,
        currency=tx.currency,
        timestamp=tx.timestamp,
        metadata=tx.metadata,
    )
