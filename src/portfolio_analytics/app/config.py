"""
Application configuration.

All tunables are centralised here so they can be overridden via
environment variables or a future config file without touching
business logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class AppConfig:
    """Top-level configuration for the portfolio analytics application."""

    # Database
    db_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("PA_DB_PATH", "portfolio_analytics.sqlite3")
        )
    )

    # Pricing
    pricing_base_date: date = date(2024, 1, 1)

    # Mock data
    demo_portfolio_id: str = "demo-portfolio-1"
    demo_client_name: str = "Demo Client"

    # API
    api_host: str = os.environ.get("PA_API_HOST", "0.0.0.0")
    api_port: int = int(os.environ.get("PA_API_PORT", "8000"))

    # Streamlit
    streamlit_page_title: str = "Portfolio Analytics"
