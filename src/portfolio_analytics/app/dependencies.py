"""
Simple dependency injection — wires repositories, services, and routes.

This module is the **composition root**: it creates every concrete
implementation once and hands them to the layers that need them.

Usage::

    from portfolio_analytics.app.dependencies import bootstrap
    container = bootstrap()          # uses default config
    container = bootstrap(config)    # uses custom config
"""

from __future__ import annotations

from dataclasses import dataclass

from portfolio_analytics.app.config import AppConfig
from portfolio_analytics.db.connection import Database
from portfolio_analytics.domain.interfaces import (
    FXServiceBase,
    PortfolioAnalyticsServiceBase,
    PricingServiceBase,
    TransactionServiceBase,
)
from portfolio_analytics.mock.data_generator import generate_portfolio
from portfolio_analytics.repositories.base import (
    CashAccountRepository,
    ClientRepository,
    InstrumentRepository,
    PortfolioRepository,
    TransactionRepository,
)
from portfolio_analytics.repositories.sqlite_repos import (
    SqliteCashAccountRepository,
    SqliteClientRepository,
    SqliteInstrumentRepository,
    SqlitePortfolioRepository,
    SqliteTransactionRepository,
)
from portfolio_analytics.services.fx_service import MockFXService
from portfolio_analytics.services.portfolio_analytics_service import (
    PortfolioAnalyticsService,
)
from portfolio_analytics.services.pricing_service import MockPricingService
from portfolio_analytics.services.transaction_service import TransactionService


@dataclass
class Container:
    """Holds all wired-up components for easy access."""

    config: AppConfig
    db: Database

    # Repositories
    client_repo: ClientRepository
    portfolio_repo: PortfolioRepository
    instrument_repo: InstrumentRepository
    cash_account_repo: CashAccountRepository
    transaction_repo: TransactionRepository

    # Services
    pricing_service: PricingServiceBase
    fx_service: FXServiceBase
    transaction_service: TransactionServiceBase
    analytics_service: PortfolioAnalyticsServiceBase


def bootstrap(config: AppConfig | None = None) -> Container:
    """
    Create and wire all components.

    If no demo data exists in the database, a mock portfolio is generated
    automatically so the app starts with realistic content.
    """
    cfg = config or AppConfig()

    db = Database(cfg.db_path)

    # Repositories
    client_repo = SqliteClientRepository(db)
    portfolio_repo = SqlitePortfolioRepository(db)
    instrument_repo = SqliteInstrumentRepository(db)
    cash_account_repo = SqliteCashAccountRepository(db)
    transaction_repo = SqliteTransactionRepository(db)

    # Services
    fx_service = MockFXService()
    pricing_service = MockPricingService(instrument_repo, cfg.pricing_base_date)
    transaction_service = TransactionService(
        portfolio_repo=portfolio_repo,
        instrument_repo=instrument_repo,
        cash_account_repo=cash_account_repo,
        transaction_repo=transaction_repo,
        fx_service=fx_service,
    )
    analytics_service = PortfolioAnalyticsService(
        portfolio_repo=portfolio_repo,
        instrument_repo=instrument_repo,
        transaction_repo=transaction_repo,
        cash_account_repo=cash_account_repo,
        pricing_service=pricing_service,
        fx_service=fx_service,
    )

    container = Container(
        config=cfg,
        db=db,
        client_repo=client_repo,
        portfolio_repo=portfolio_repo,
        instrument_repo=instrument_repo,
        cash_account_repo=cash_account_repo,
        transaction_repo=transaction_repo,
        pricing_service=pricing_service,
        fx_service=fx_service,
        transaction_service=transaction_service,
        analytics_service=analytics_service,
    )

    # Seed demo data if the database is empty
    _seed_if_empty(container)

    return container


def wire_routes(container: Container) -> None:
    """Inject service references into the FastAPI route module."""
    from portfolio_analytics.api import routes

    routes.analytics_service = container.analytics_service
    routes.pricing_service = container.pricing_service
    routes.fx_service = container.fx_service
    routes.instrument_repo = container.instrument_repo
    routes.transaction_repo = container.transaction_repo


def _seed_if_empty(container: Container) -> None:
    """Generate mock data when the database has no clients."""
    if container.client_repo.list_all():
        return  # already seeded

    data = generate_portfolio(
        portfolio_id=container.config.demo_portfolio_id,
        client_name=container.config.demo_client_name,
    )

    container.client_repo.save(data["client"])
    container.portfolio_repo.save(data["portfolio"])
    for inst in data["instruments"]:
        container.instrument_repo.save(inst)
    for ca in data["cash_accounts"]:
        container.cash_account_repo.save(ca)
    for tx in data["transactions"]:
        container.transaction_repo.save(tx)
