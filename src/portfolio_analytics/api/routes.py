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
    InstrumentResponse,
    PortfolioOverviewResponse,
    PriceResponse,
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
