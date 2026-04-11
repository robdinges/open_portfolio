"""
Test suite for the portfolio_analytics package.

Covers:
    • Domain models and enums
    • Database schema creation and reset
    • Repository CRUD operations
    • Mock pricing and FX services (determinism)
    • Transaction engine (buy, sell, FX, fee, interest + validations)
    • Portfolio analytics (holdings, value, allocation, P&L)
    • Mock data generator (determinism and structure)
    • FastAPI endpoints
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import date, datetime, timedelta

import pytest

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------
from portfolio_analytics.domain.enums import (
    AllocationDimension,
    InstrumentType,
    TransactionType,
)
from portfolio_analytics.domain.models import (
    AllocationEntry,
    CashAccount,
    Client,
    Holding,
    Instrument,
    InstrumentAttributeHistory,
    Portfolio,
    PortfolioOverview,
    Transaction,
)

# ---------------------------------------------------------------------------
# DB + Repositories
# ---------------------------------------------------------------------------
from portfolio_analytics.db.connection import Database
from portfolio_analytics.repositories.sqlite_repos import (
    SqliteCashAccountRepository,
    SqliteClientRepository,
    SqliteInstrumentRepository,
    SqlitePortfolioRepository,
    SqliteTransactionRepository,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
from portfolio_analytics.services.fx_service import MockFXService
from portfolio_analytics.services.pricing_service import MockPricingService
from portfolio_analytics.services.transaction_service import TransactionService
from portfolio_analytics.services.portfolio_analytics_service import (
    PortfolioAnalyticsService,
)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------
from portfolio_analytics.mock.data_generator import generate_portfolio


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def db(tmp_path):
    """Fresh in-memory-style database for each test."""
    return Database(tmp_path / "test.sqlite3")


@pytest.fixture
def repos(db):
    """All five repository instances sharing one database."""
    return {
        "client": SqliteClientRepository(db),
        "portfolio": SqlitePortfolioRepository(db),
        "instrument": SqliteInstrumentRepository(db),
        "cash_account": SqliteCashAccountRepository(db),
        "transaction": SqliteTransactionRepository(db),
    }


@pytest.fixture
def sample_client():
    return Client(id="C-001", name="Alice Johnson")


@pytest.fixture
def sample_portfolio():
    return Portfolio(id="P-001", name="Growth EUR", client_id="C-001", base_currency="EUR")


@pytest.fixture
def sample_stocks():
    return [
        Instrument(id="STK-001", name="Apple Inc.", type=InstrumentType.STOCK, currency="USD"),
        Instrument(id="STK-002", name="ASML Holding", type=InstrumentType.STOCK, currency="EUR"),
    ]


@pytest.fixture
def sample_bond():
    return Instrument(
        id="BND-001",
        name="German Bund 2.5% 2034",
        type=InstrumentType.BOND,
        currency="EUR",
        metadata={"coupon_rate": 2.5, "maturity_year": 2034},
    )


@pytest.fixture
def fx_service():
    return MockFXService()


@pytest.fixture
def seeded_repos(db, repos, sample_client, sample_portfolio, sample_stocks, sample_bond):
    """Repos pre-populated with client, portfolio, instruments, and cash accounts."""
    repos["client"].save(sample_client)
    repos["portfolio"].save(sample_portfolio)
    for s in sample_stocks:
        repos["instrument"].save(s)
    repos["instrument"].save(sample_bond)
    repos["cash_account"].save(CashAccount(id="CA-EUR", portfolio_id="P-001", currency="EUR"))
    repos["cash_account"].save(CashAccount(id="CA-USD", portfolio_id="P-001", currency="USD"))
    return repos


# ===================================================================
# Domain model tests
# ===================================================================


class TestDomainModels:

    def test_instrument_creation(self):
        inst = Instrument(id="X", name="Test", type=InstrumentType.STOCK, currency="USD")
        assert inst.type == InstrumentType.STOCK
        assert inst.metadata == {}

    def test_transaction_metadata_default(self):
        tx = Transaction(
            id="T1", portfolio_id="P1", instrument_id=None,
            type=TransactionType.FEE, quantity=0, price=0,
            amount=-10.0, currency="EUR", timestamp=datetime.now(),
        )
        assert tx.metadata == {}

    def test_enum_string_values(self):
        assert TransactionType.BUY.value == "BUY"
        assert InstrumentType.BOND.value == "BOND"
        assert AllocationDimension.ASSET_CLASS.value == "asset_class"


# ===================================================================
# Database tests
# ===================================================================


class TestDatabase:

    def test_schema_creation(self, db):
        conn = db.connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {r["name"] for r in tables}
        assert "clients" in table_names
        assert "transactions" in table_names
        assert "instrument_attributes_history" in table_names
        conn.close()

    def test_reset(self, db):
        conn = db.connect()
        conn.execute("INSERT INTO clients (id, name) VALUES ('X', 'Test')")
        conn.commit()
        conn.close()
        db.reset()
        conn = db.connect()
        count = conn.execute("SELECT COUNT(*) as c FROM clients").fetchone()["c"]
        assert count == 0
        conn.close()


# ===================================================================
# Repository tests
# ===================================================================


class TestClientRepository:

    def test_save_and_get(self, repos, sample_client):
        repos["client"].save(sample_client)
        loaded = repos["client"].get("C-001")
        assert loaded is not None
        assert loaded.name == "Alice Johnson"

    def test_list_all(self, repos):
        repos["client"].save(Client(id="A", name="Alpha"))
        repos["client"].save(Client(id="B", name="Beta"))
        clients = repos["client"].list_all()
        assert len(clients) == 2

    def test_get_nonexistent(self, repos):
        assert repos["client"].get("NOPE") is None


class TestPortfolioRepository:

    def test_save_and_get(self, repos, sample_client, sample_portfolio):
        repos["client"].save(sample_client)
        repos["portfolio"].save(sample_portfolio)
        loaded = repos["portfolio"].get("P-001")
        assert loaded is not None
        assert loaded.base_currency == "EUR"

    def test_list_by_client(self, repos, sample_client):
        repos["client"].save(sample_client)
        repos["portfolio"].save(
            Portfolio(id="P-1", name="A", client_id="C-001", base_currency="EUR")
        )
        repos["portfolio"].save(
            Portfolio(id="P-2", name="B", client_id="C-001", base_currency="USD")
        )
        result = repos["portfolio"].list_by_client("C-001")
        assert len(result) == 2


class TestInstrumentRepository:

    def test_save_and_get(self, repos, sample_stocks):
        repos["instrument"].save(sample_stocks[0])
        loaded = repos["instrument"].get("STK-001")
        assert loaded.name == "Apple Inc."
        assert loaded.type == InstrumentType.STOCK

    def test_metadata_roundtrip(self, repos, sample_bond):
        repos["instrument"].save(sample_bond)
        loaded = repos["instrument"].get("BND-001")
        assert loaded.metadata["coupon_rate"] == 2.5

    def test_attribute_history(self, repos, sample_stocks):
        repos["instrument"].save(sample_stocks[0])
        repos["instrument"].save_attribute(
            InstrumentAttributeHistory(
                instrument_id="STK-001",
                attribute_name="sector",
                attribute_value="Technology",
                valid_from=datetime(2024, 1, 1),
                valid_to=datetime(2025, 1, 1),
            )
        )
        repos["instrument"].save_attribute(
            InstrumentAttributeHistory(
                instrument_id="STK-001",
                attribute_name="sector",
                attribute_value="Consumer Electronics",
                valid_from=datetime(2025, 1, 1),
            )
        )
        val_2024 = repos["instrument"].get_attribute(
            "STK-001", "sector", datetime(2024, 6, 1)
        )
        assert val_2024 == "Technology"
        val_2025 = repos["instrument"].get_attribute(
            "STK-001", "sector", datetime(2025, 6, 1)
        )
        assert val_2025 == "Consumer Electronics"


class TestTransactionRepository:

    def test_save_and_list(self, seeded_repos):
        tx = Transaction(
            id="TX-001", portfolio_id="P-001", instrument_id="STK-001",
            type=TransactionType.BUY, quantity=10, price=150.0,
            amount=-1500.0, currency="USD",
            timestamp=datetime(2024, 6, 1, 10, 0, 0),
        )
        seeded_repos["transaction"].save(tx)
        loaded = seeded_repos["transaction"].list_by_portfolio("P-001")
        assert len(loaded) == 1
        assert loaded[0].quantity == 10

    def test_list_with_cutoff(self, seeded_repos):
        for i, d in enumerate([datetime(2024, 3, 1), datetime(2024, 6, 1), datetime(2024, 9, 1)]):
            seeded_repos["transaction"].save(
                Transaction(
                    id=f"TX-{i}", portfolio_id="P-001", instrument_id="STK-001",
                    type=TransactionType.BUY, quantity=10, price=100.0,
                    amount=-1000.0, currency="EUR", timestamp=d,
                )
            )
        before_july = seeded_repos["transaction"].list_by_portfolio(
            "P-001", up_to=datetime(2024, 7, 1)
        )
        assert len(before_july) == 2


# ===================================================================
# Pricing service tests
# ===================================================================


class TestMockPricingService:

    def test_deterministic(self, seeded_repos):
        svc = MockPricingService(seeded_repos["instrument"])
        p1 = svc.get_price("STK-001", date(2025, 6, 1))
        p2 = svc.get_price("STK-001", date(2025, 6, 1))
        assert p1 == p2

    def test_price_series(self, seeded_repos):
        svc = MockPricingService(seeded_repos["instrument"])
        series = svc.get_price_series("STK-001", date(2025, 1, 1), date(2025, 1, 10))
        assert len(series) > 0
        assert all(isinstance(p, float) for _, p in series)

    def test_bond_price_near_par(self, seeded_repos):
        svc = MockPricingService(seeded_repos["instrument"])
        price = svc.get_price("BND-001", date(2025, 6, 1))
        assert 50 < price < 150  # mean-reverting around 100

    def test_unknown_instrument_raises(self, seeded_repos):
        svc = MockPricingService(seeded_repos["instrument"])
        with pytest.raises(ValueError, match="Unknown instrument"):
            svc.get_price("NONEXISTENT", date(2025, 1, 1))


# ===================================================================
# FX service tests
# ===================================================================


class TestMockFXService:

    def test_same_currency(self, fx_service):
        assert fx_service.get_fx_rate("EUR", "EUR", date(2025, 1, 1)) == 1.0

    def test_usd_to_eur(self, fx_service):
        rate = fx_service.get_fx_rate("USD", "EUR", date(2025, 1, 1))
        assert 0.85 < rate < 0.97  # roughly 0.91

    def test_deterministic(self, fx_service):
        r1 = fx_service.get_fx_rate("GBP", "EUR", date(2025, 3, 15))
        r2 = fx_service.get_fx_rate("GBP", "EUR", date(2025, 3, 15))
        assert r1 == r2

    def test_unsupported_raises(self, fx_service):
        with pytest.raises(ValueError, match="Unsupported currency"):
            fx_service.get_fx_rate("XYZ", "EUR", date(2025, 1, 1))


# ===================================================================
# Transaction engine tests
# ===================================================================


class TestTransactionService:

    def _make_service(self, repos, fx_service):
        return TransactionService(
            portfolio_repo=repos["portfolio"],
            instrument_repo=repos["instrument"],
            cash_account_repo=repos["cash_account"],
            transaction_repo=repos["transaction"],
            fx_service=fx_service,
        )

    def _deposit_cash(self, repos, currency, amount):
        repos["transaction"].save(
            Transaction(
                id=str(uuid.uuid4()), portfolio_id="P-001", instrument_id=None,
                type=TransactionType.INTEREST, quantity=0, price=0,
                amount=amount, currency=currency,
                timestamp=datetime(2024, 1, 1),
            )
        )

    def test_buy_reduces_cash(self, seeded_repos, fx_service):
        self._deposit_cash(seeded_repos, "EUR", 100_000)
        svc = self._make_service(seeded_repos, fx_service)
        tx = svc.execute_buy("P-001", "STK-002", 10, 700.0, datetime(2024, 6, 1, 10, 0))
        assert tx.type == TransactionType.BUY
        assert tx.amount < 0  # cash outflow

    def test_sell_increases_cash(self, seeded_repos, fx_service):
        self._deposit_cash(seeded_repos, "EUR", 100_000)
        svc = self._make_service(seeded_repos, fx_service)
        svc.execute_buy("P-001", "STK-002", 10, 700.0, datetime(2024, 6, 1, 10, 0))
        tx = svc.execute_sell("P-001", "STK-002", 5, 750.0, datetime(2024, 7, 1, 10, 0))
        assert tx.type == TransactionType.SELL
        assert tx.amount > 0  # cash inflow

    def test_insufficient_cash_raises(self, seeded_repos, fx_service):
        svc = self._make_service(seeded_repos, fx_service)
        with pytest.raises(ValueError, match="Insufficient cash"):
            svc.execute_buy("P-001", "STK-002", 100, 1000.0, datetime(2024, 6, 1))

    def test_insufficient_position_raises(self, seeded_repos, fx_service):
        self._deposit_cash(seeded_repos, "EUR", 100_000)
        svc = self._make_service(seeded_repos, fx_service)
        with pytest.raises(ValueError, match="Insufficient position"):
            svc.execute_sell("P-001", "STK-002", 10, 100.0, datetime(2024, 6, 1))

    def test_fx_conversion(self, seeded_repos, fx_service):
        self._deposit_cash(seeded_repos, "EUR", 50_000)
        svc = self._make_service(seeded_repos, fx_service)
        tx_debit, tx_credit = svc.execute_fx(
            "P-001", "EUR", "USD", 10_000, 1.09, datetime(2024, 6, 1)
        )
        assert tx_debit.amount == -10_000
        assert tx_credit.amount == 10_900
        assert tx_debit.currency == "EUR"
        assert tx_credit.currency == "USD"

    def test_fee_deducted(self, seeded_repos, fx_service):
        self._deposit_cash(seeded_repos, "EUR", 100_000)
        svc = self._make_service(seeded_repos, fx_service)
        tx = svc.execute_fee("P-001", 25.0, "EUR", datetime(2024, 6, 1))
        assert tx.amount == -25.0

    def test_interest_credited(self, seeded_repos, fx_service):
        svc = self._make_service(seeded_repos, fx_service)
        tx = svc.execute_interest("P-001", 150.0, "EUR", datetime(2024, 6, 1), "BND-001")
        assert tx.amount == 150.0

    def test_unknown_portfolio_raises(self, seeded_repos, fx_service):
        svc = self._make_service(seeded_repos, fx_service)
        with pytest.raises(ValueError, match="Portfolio not found"):
            svc.execute_buy("NOPE", "STK-001", 1, 100, datetime(2024, 6, 1))

    def test_usd_settlement_when_account_exists(self, seeded_repos, fx_service):
        """USD instrument settles in USD when a USD cash account exists."""
        self._deposit_cash(seeded_repos, "USD", 50_000)
        svc = self._make_service(seeded_repos, fx_service)
        tx = svc.execute_buy("P-001", "STK-001", 5, 150.0, datetime(2024, 6, 1))
        assert tx.currency == "USD"


# ===================================================================
# Portfolio analytics tests
# ===================================================================


class TestPortfolioAnalytics:

    def _setup(self, seeded_repos, fx_service):
        pricing = MockPricingService(seeded_repos["instrument"])
        analytics = PortfolioAnalyticsService(
            portfolio_repo=seeded_repos["portfolio"],
            instrument_repo=seeded_repos["instrument"],
            transaction_repo=seeded_repos["transaction"],
            cash_account_repo=seeded_repos["cash_account"],
            pricing_service=pricing,
            fx_service=fx_service,
        )
        # Seed cash and trades
        seeded_repos["transaction"].save(
            Transaction(
                id="SEED-CASH", portfolio_id="P-001", instrument_id=None,
                type=TransactionType.INTEREST, quantity=0, price=0,
                amount=100_000.0, currency="EUR",
                timestamp=datetime(2024, 1, 1),
            )
        )
        seeded_repos["transaction"].save(
            Transaction(
                id="SEED-BUY-1", portfolio_id="P-001", instrument_id="STK-002",
                type=TransactionType.BUY, quantity=20, price=700.0,
                amount=-14_000.0, currency="EUR",
                timestamp=datetime(2024, 3, 1, 10, 0),
            )
        )
        seeded_repos["transaction"].save(
            Transaction(
                id="SEED-BUY-2", portfolio_id="P-001", instrument_id="STK-002",
                type=TransactionType.BUY, quantity=10, price=750.0,
                amount=-7_500.0, currency="EUR",
                timestamp=datetime(2024, 6, 1, 10, 0),
            )
        )
        return analytics, pricing

    def test_get_holdings(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        holdings = analytics.get_holdings("P-001", datetime(2024, 7, 1))
        assert len(holdings) == 1
        h = holdings[0]
        assert h.instrument_id == "STK-002"
        assert h.quantity == 30

    def test_average_cost(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        holdings = analytics.get_holdings("P-001", datetime(2024, 7, 1))
        h = holdings[0]
        # avg cost = (20*700 + 10*750) / 30 ≈ 716.67 (in EUR, fx ~1.0 for EUR/EUR)
        assert 710 < h.average_cost < 725

    def test_allocation(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        alloc = analytics.get_allocation(
            "P-001", AllocationDimension.ASSET_CLASS, datetime(2024, 7, 1)
        )
        assert len(alloc) == 1
        assert alloc[0].label == "STOCK"
        assert alloc[0].weight == 1.0

    def test_portfolio_value_includes_cash(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        value = analytics.get_portfolio_value("P-001", datetime(2024, 7, 1))
        assert value > 0

    def test_overview(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        overview = analytics.get_overview("P-001", datetime(2024, 7, 1))
        assert isinstance(overview, PortfolioOverview)
        assert overview.currency == "EUR"
        assert len(overview.holdings) == 1

    def test_historical_reconstruction(self, seeded_repos, fx_service):
        """Holdings at different points in time should differ."""
        analytics, _ = self._setup(seeded_repos, fx_service)
        h_march = analytics.get_holdings("P-001", datetime(2024, 4, 1))
        h_july = analytics.get_holdings("P-001", datetime(2024, 7, 1))
        assert h_march[0].quantity == 20  # only first buy
        assert h_july[0].quantity == 30   # both buys

    def test_empty_portfolio(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        holdings = analytics.get_holdings("P-001", datetime(2023, 1, 1))
        assert holdings == []

    def test_bond_analytics_report(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        seeded_repos["transaction"].save(
            Transaction(
                id="BOND-BUY", portfolio_id="P-001", instrument_id="BND-001",
                type=TransactionType.BUY, quantity=5000, price=99.5,
                amount=-497500.0, currency="EUR",
                timestamp=datetime(2024, 4, 1, 10, 0),
            )
        )
        report = analytics.get_bond_analytics("P-001", datetime(2024, 7, 1))
        assert report.portfolio_id == "P-001"
        assert len(report.entries) == 1
        assert report.entries[0].dirty_price >= report.entries[0].clean_price

    def test_performance_report(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        report = analytics.get_performance_report("P-001", datetime(2024, 7, 1), 63)
        assert report.portfolio_id == "P-001"
        assert len(report.series) > 5
        assert report.start_date < report.as_of

    def test_risk_metrics(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        report = analytics.get_risk_metrics("P-001", datetime(2024, 7, 1), 63)
        assert report.portfolio_id == "P-001"
        assert report.annualized_volatility >= 0
        assert report.var_95 >= 0

    def test_attribution_report(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        report = analytics.get_attribution_report("P-001", datetime(2024, 7, 1))
        assert report.by_instrument
        assert report.by_asset_class

    def test_data_quality_report(self, seeded_repos, fx_service):
        analytics, _ = self._setup(seeded_repos, fx_service)
        report = analytics.get_data_quality_report("P-001", datetime(2024, 7, 1))
        assert report.portfolio_id == "P-001"
        assert report.coverage_pct >= 0


# ===================================================================
# Mock data generator tests
# ===================================================================


class TestDataGenerator:

    def test_deterministic(self):
        d1 = generate_portfolio("test-seed-1")
        d2 = generate_portfolio("test-seed-1")
        assert d1["client"].id == d2["client"].id
        assert len(d1["transactions"]) == len(d2["transactions"])
        assert d1["transactions"][0].id == d2["transactions"][0].id

    def test_different_seeds_differ(self):
        d1 = generate_portfolio("seed-alpha")
        d2 = generate_portfolio("seed-beta")
        assert d1["client"].id != d2["client"].id

    def test_structure(self):
        data = generate_portfolio("struct-test")
        assert isinstance(data["client"], Client)
        assert isinstance(data["portfolio"], Portfolio)
        assert 5 <= len(data["instruments"]) <= 10
        assert len(data["cash_accounts"]) >= 1
        assert 50 < len(data["transactions"]) < 500

    def test_instruments_are_mixed(self):
        data = generate_portfolio("mix-test")
        types = {i.type for i in data["instruments"]}
        assert InstrumentType.STOCK in types
        assert InstrumentType.BOND in types


# ===================================================================
# FastAPI endpoint tests
# ===================================================================


class TestFastAPI:

    @pytest.fixture
    def client(self, tmp_path):
        """Create a TestClient with a fresh DB and demo data."""
        import os
        os.environ["PA_DB_PATH"] = str(tmp_path / "api_test.sqlite3")

        # Force fresh bootstrap
        from portfolio_analytics.app import main as main_module
        from portfolio_analytics.app.config import AppConfig
        from portfolio_analytics.app.dependencies import bootstrap, wire_routes

        cfg = AppConfig(db_path=tmp_path / "api_test.sqlite3")
        container = bootstrap(cfg)
        wire_routes(container)

        from fastapi.testclient import TestClient
        tc = TestClient(main_module.app)
        tc._container = container  # keep reference for assertions
        return tc

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_portfolio_overview(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/overview?date=2025-06-01")
        assert resp.status_code == 200
        body = resp.json()
        assert "portfolio_value" in body
        assert "holdings" in body

    def test_allocation(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/allocation?by=asset_class&date=2025-06-01")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_transactions(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/transactions")
        assert resp.status_code == 200
        txs = resp.json()
        assert len(txs) > 0

    def test_instrument_detail(self, client):
        instruments = client._container.instrument_repo.list_all()
        resp = client.get(f"/instrument/{instruments[0].id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == instruments[0].name

    def test_pricing(self, client):
        instruments = client._container.instrument_repo.list_all()
        resp = client.get(f"/pricing/{instruments[0].id}?date=2025-06-01")
        assert resp.status_code == 200
        assert "price" in resp.json()

    def test_not_found_portfolio(self, client):
        resp = client.get("/portfolio/NONEXISTENT/overview")
        assert resp.status_code == 404

    def test_invalid_date(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/overview?date=not-a-date")
        assert resp.status_code == 400

    def test_bond_analytics_endpoint(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/bond-analytics?date=2025-06-01")
        assert resp.status_code == 200
        assert "entries" in resp.json()

    def test_performance_endpoint(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/performance?date=2025-06-01&lookback_days=126")
        assert resp.status_code == 200
        assert "series" in resp.json()

    def test_risk_endpoint(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/risk?date=2025-06-01&lookback_days=126")
        assert resp.status_code == 200
        assert "annualized_volatility" in resp.json()

    def test_attribution_endpoint(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/attribution?date=2025-06-01")
        assert resp.status_code == 200
        assert "by_instrument" in resp.json()

    def test_data_quality_endpoint(self, client):
        pid = client._container.config.demo_portfolio_id
        resp = client.get(f"/portfolio/{pid}/data-quality?date=2025-06-01")
        assert resp.status_code == 200
        assert "coverage_pct" in resp.json()
