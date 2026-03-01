import os

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
