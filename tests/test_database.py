import os
import threading
from datetime import datetime, UTC, timedelta

import pytest

from open_portfolio.database import Database
from open_portfolio.clients import Client


def test_database_client_portfolio(tmp_path):
    db_file = tmp_path / "demo.db"
    db = Database(str(db_file))

    # create client and portfolio
    client = Client(client_id=42, name="Test User")
    portfolio = client.add_portfolio(portfolio_id=100)

    # save to database
    db.add_client(client)
    db.add_portfolio(portfolio)

    # read back
    clients = db.get_clients()
    assert clients == [{"client_id": 42, "name": "Test User"}]

    portfolios = db.get_portfolios()
    assert portfolios == [
        {
            "portfolio_id": 100,
            "client_id": 42,
            "name": "Test User",
            "default_currency": "EUR",
            "cost_in_transaction_currency": True,
        }
    ]

    # cleanup
    db.close()
    assert db_file.exists()


def test_database_order_draft_persistence(tmp_path):
    db_file = tmp_path / "orders.db"
    db = Database(str(db_file))

    db.upsert_order_draft(
        draft_id="OD-000001",
        portfolio_id=100,
        status="draft",
        payload={"amount": "1000", "template": "BUY"},
        errors=[],
        warnings=["placeholder"],
    )

    stored = db.get_order_draft("OD-000001")
    assert stored is not None
    assert stored["draft_id"] == "OD-000001"
    assert stored["portfolio_id"] == 100
    assert stored["status"] == "draft"
    assert stored["payload"]["amount"] == "1000"
    assert stored["warnings"] == ["placeholder"]

    db.close()


def test_database_purge_stale_order_drafts_keeps_submitted(tmp_path):
    db_file = tmp_path / "orders_retention.db"
    db = Database(str(db_file))

    old_ts = (datetime.now(UTC) - timedelta(days=60)).isoformat(timespec="seconds")
    new_ts = datetime.now(UTC).isoformat(timespec="seconds")

    db.upsert_order_draft(
        draft_id="OD-OLD-DRAFT",
        portfolio_id=1,
        status="draft",
        payload={"k": "v"},
        created_at=old_ts,
        updated_at=old_ts,
    )
    db.upsert_order_draft(
        draft_id="OD-OLD-SUB",
        portfolio_id=1,
        status="submitted",
        payload={"k": "v"},
        created_at=old_ts,
        updated_at=old_ts,
    )
    db.upsert_order_draft(
        draft_id="OD-NEW-DRAFT",
        portfolio_id=1,
        status="draft",
        payload={"k": "v"},
        created_at=new_ts,
        updated_at=new_ts,
    )

    deleted = db.purge_stale_order_drafts(retention_days=30)
    assert deleted == 1
    assert db.get_order_draft("OD-OLD-DRAFT") is None
    assert db.get_order_draft("OD-OLD-SUB") is not None
    assert db.get_order_draft("OD-NEW-DRAFT") is not None

    db.close()


def test_database_order_draft_status_counts_and_list(tmp_path):
    db_file = tmp_path / "orders_summary.db"
    db = Database(str(db_file))

    db.upsert_order_draft(
        draft_id="OD-1",
        portfolio_id=10,
        status="draft",
        payload={"template": "BUY"},
    )
    db.upsert_order_draft(
        draft_id="OD-2",
        portfolio_id=10,
        status="draft",
        payload={"template": "SELL"},
    )
    db.upsert_order_draft(
        draft_id="OD-3",
        portfolio_id=11,
        status="validated",
        payload={"template": "BUY"},
    )

    counts = db.get_order_draft_status_counts()
    assert counts["draft"] == 2
    assert counts["validated"] == 1

    listed = db.list_order_drafts(limit=2)
    assert len(listed) == 2
    assert all("draft_id" in row for row in listed)

    db.close()


def test_database_allows_cross_thread_usage_for_order_drafts(tmp_path):
    db_file = tmp_path / "orders_thread.db"
    db = Database(str(db_file))

    result = {"ok": False, "error": ""}

    def worker():
        try:
            db.upsert_order_draft(
                draft_id="OD-THREAD-1",
                portfolio_id=1,
                status="draft",
                payload={"template": "BUY"},
            )
            stored = db.get_order_draft("OD-THREAD-1")
            result["ok"] = stored is not None
        except Exception as exc:  # pragma: no cover - diagnostic capture
            result["error"] = str(exc)

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert result["ok"], result["error"]
    db.close()


def test_database_instrument_persistence_roundtrip(tmp_path):
    db_file = tmp_path / "instrument_roundtrip.db"
    db = Database(str(db_file))

    db.upsert_instrument(
        {
            "instrument_id": 987001,
            "description": "Roundtrip Option",
            "instrument_type": "OPTION",
            "issue_currency": "USD",
            "minimum_purchase_value": 1,
            "smallest_trading_unit": 1,
            "start_date": None,
            "maturity_date": None,
            "interest_rate": None,
            "interest_payment_frequency": None,
        }
    )

    rows = db.list_instruments()
    row = next((r for r in rows if r["instrument_id"] == 987001), None)
    assert row is not None
    assert row["description"] == "Roundtrip Option"
    assert row["instrument_type"] == "OPTION"
    assert row["issue_currency"] == "USD"

    db.close()
