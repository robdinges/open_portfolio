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
