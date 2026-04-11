"""
Pydantic response schemas for the REST API.

These models define the JSON shape that clients receive.  They are
serialised automatically by FastAPI and appear in the OpenAPI docs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HoldingResponse(BaseModel):
    instrument_id: str
    instrument_name: str
    instrument_type: str
    quantity: float
    average_cost: float
    market_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    allocation_pct: float
    currency: str


class PortfolioOverviewResponse(BaseModel):
    portfolio_id: str
    portfolio_value: float
    currency: str
    holdings: list[HoldingResponse]
    cash_balances: dict[str, float]
    unrealized_pnl: float
    as_of: datetime


class AllocationEntryResponse(BaseModel):
    label: str
    market_value: float
    weight: float


class TransactionResponse(BaseModel):
    id: str
    portfolio_id: str
    instrument_id: Optional[str]
    type: str
    quantity: float
    price: float
    amount: float
    currency: str
    timestamp: datetime
    metadata: dict


class InstrumentResponse(BaseModel):
    id: str
    name: str
    type: str
    currency: str
    metadata: dict


class PriceResponse(BaseModel):
    instrument_id: str
    date: str
    price: float


class BondAnalyticsEntryResponse(BaseModel):
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


class BondAnalyticsReportResponse(BaseModel):
    portfolio_id: str
    currency: str
    as_of: datetime
    entries: list[BondAnalyticsEntryResponse]
    total_accrued_interest: float
    total_dirty_value: float
    average_ytm: float


class PerformancePointResponse(BaseModel):
    timestamp: datetime
    portfolio_value: float


class HoldingPerformanceResponse(BaseModel):
    instrument_id: str
    instrument_name: str
    instrument_type: str
    start_price: float
    end_price: float
    total_return: float
    annualized_return: float
    weight: float
    pnl_contribution: float


class PerformanceReportResponse(BaseModel):
    portfolio_id: str
    currency: str
    as_of: datetime
    start_date: datetime
    total_return: float
    annualized_return: float
    money_weighted_return: float
    time_weighted_return: float
    max_drawdown: float
    series: list[PerformancePointResponse]
    holdings: list[HoldingPerformanceResponse]


class RiskMetricsReportResponse(BaseModel):
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


class AttributionEntryResponse(BaseModel):
    label: str
    market_value: float
    weight: float
    unrealized_pnl: float
    pnl_contribution: float


class AttributionReportResponse(BaseModel):
    portfolio_id: str
    currency: str
    as_of: datetime
    by_instrument: list[AttributionEntryResponse]
    by_asset_class: list[AttributionEntryResponse]


class DataQualityIssueResponse(BaseModel):
    instrument_id: str
    instrument_name: str
    severity: str
    field_name: str
    message: str


class DataQualityReportResponse(BaseModel):
    portfolio_id: str
    as_of: datetime
    coverage_pct: float
    issues: list[DataQualityIssueResponse]
