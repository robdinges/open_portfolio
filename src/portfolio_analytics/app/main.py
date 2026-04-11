"""
FastAPI application entry point.

Run with::

    PYTHONPATH=src uvicorn portfolio_analytics.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from portfolio_analytics.api.routes import router
from portfolio_analytics.app.dependencies import bootstrap, wire_routes

app = FastAPI(
    title="Portfolio Analytics API",
    version="0.1.0",
    description="Modular portfolio analysis MVP with mock data.",
)

# Bootstrap and wire dependencies on startup
_container = bootstrap()
wire_routes(_container)

app.include_router(router)
