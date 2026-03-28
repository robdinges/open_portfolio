import pytest
from open_portfolio.web_app import make_app, create_demo_data
from open_portfolio.product_collection import ProductCollection
from open_portfolio.database import Database


def test_transaction_summary_shown():
    # build app with demo data
    client, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(client, pc, prices)
    with app.test_client() as c:
        # perform a buy transaction on portfolio 1
        resp = c.post(
            "/transactions/new",
            data={
                "portfolio_id": "1",
                "template": "BUY",
                "product_id": str(products_list[0].instrument_id),
                "amount": "5",
                "price": "100",
            },
        )
        assert resp.status_code == 200


def test_index_page_contains_portfolio():
    client, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(client, pc, prices)
    with app.test_client() as c:
        r = c.get("/")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "Portefeuilles" in html
        # the first client's name should appear in the overview
        assert client[0].name in html


def test_sell_with_insufficient_position_shows_error():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        selected_client = clients[0]
        selected_portfolio = next((p for p in selected_client.portfolios if p.portfolio_id == 2), selected_client.portfolios[0])

        holding = selected_portfolio.securities_account.holdings[0]
        if isinstance(holding, dict):
            product_id = holding["product"].instrument_id
            current_amount = float(holding["amount"])
        else:
            product_id = holding.product.instrument_id
            current_amount = float(holding.amount)

        response = c.post(
            "/transactions/new",
            data={
                "client_id": str(selected_client.client_id),
                "portfolio_id": str(selected_portfolio.portfolio_id),
                "template": "SELL",
                "product_id": str(product_id),
                "amount": str(current_amount + 1),
                "price": "100",
                "save": "1",
            },
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Onvoldoende positie voor verkoop" in html


def test_market_sell_accepts_decimal_comma_and_redirects():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.post(
            "/transactions/new",
            data={
                "client_id": "1",
                "portfolio_id": "2",
                "template": "SELL",
                "order_type": "MARKET",
                "product_id": "1",
                "amount": "1,0",
                "transaction_date": "2026-03-01",
                "settlement_currency": "USD",
                "save": "1",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("Location", "")
        assert "/transactions" in location
        assert "client_id=1" in location
        assert "portfolio_id=2" in location


def test_limit_bond_form_shows_percent_suffix_and_nominal_label():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.get(
            "/transactions/new?client_id=1&portfolio_id=1&template=BUY&order_type=LIMIT&product_id=101"
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Nominale waarde" in html
        assert ">%</span>" in html


def test_same_currency_settlement_account_is_locked():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.get(
            "/transactions/new?client_id=1&portfolio_id=1&template=BUY&order_type=MARKET&product_id=5"
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Vast op portefeuillevaluta." in html
        assert "id=\"settlement_currency\" required disabled" in html


def test_form_contains_dependent_field_reset_javascript():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.get("/transactions/new")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        assert "function clearDependentFields()" in html
        assert "instrumentSelect.addEventListener(\"change\"" in html
        assert "templateSelect.addEventListener(\"change\"" in html


def test_settlement_account_populated_on_initial_form_load():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.get("/transactions/new?client_id=1&portfolio_id=1")
        assert response.status_code == 200

        html = response.get_data(as_text=True)
        assert "Afrekenrekening" in html
        assert "Saldo:" in html


def test_bond_limit_price_percent_is_converted_to_decimal_for_execution():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.post(
            "/transactions/new",
            data={
                "client_id": "1",
                "portfolio_id": "1",
                "template": "BUY",
                "order_type": "LIMIT",
                "product_id": "101",
                "amount": "1000",
                "price": "123,45",
                "transaction_date": "2026-03-01",
                "settlement_currency": "EUR",
                "save": "1",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

    portfolio = next(p for p in clients[0].portfolios if p.portfolio_id == 1)
    transactions = portfolio.list_all_transactions()
    assert transactions, "Expected at least one transaction in portfolio 1"

    bond_txs = [
        tx for tx in transactions
        if tx.get("security_movements") and tx["security_movements"][0].get("product_id") == 101
    ]
    assert bond_txs, "Expected a bond transaction for product 101"
    executed_price = float(bond_txs[-1]["security_movements"][0]["price"])
    assert executed_price == pytest.approx(1.2345)


def test_order_draft_action_shows_draft_status_and_identifier():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.post(
            "/transactions/new",
            data={
                "client_id": "1",
                "portfolio_id": "1",
                "template": "BUY",
                "order_type": "LIMIT",
                "product_id": "101",
                "amount": "1000",
                "price": "101,00",
                "transaction_date": "2026-03-01",
                "settlement_currency": "EUR",
                "action": "draft",
            },
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Conceptorder opgeslagen" in html
        assert "Orderstatus" in html
        assert "OD-" in html


def test_order_confirm_action_shows_validation_message_without_redirect():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    app = make_app(clients, pc, prices)
    with app.test_client() as c:
        response = c.post(
            "/transactions/new",
            data={
                "client_id": "1",
                "portfolio_id": "1",
                "template": "BUY",
                "order_type": "LIMIT",
                "product_id": "101",
                "amount": "1000",
                "price": "101,00",
                "transaction_date": "2026-03-01",
                "settlement_currency": "EUR",
                "action": "confirm",
            },
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Order gevalideerd" in html
        assert "Definitief boeken" in html


def test_order_draft_persists_with_database_repo_and_can_be_resumed(tmp_path):
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    db_path = tmp_path / "order_drafts.db"
    db1 = Database(str(db_path))

    app1 = make_app(clients, pc, prices, order_database=db1)
    with app1.test_client() as c:
        response = c.post(
            "/transactions/new",
            data={
                "client_id": "1",
                "portfolio_id": "1",
                "template": "BUY",
                "order_type": "LIMIT",
                "product_id": "101",
                "amount": "1000",
                "price": "101,00",
                "transaction_date": "2026-03-01",
                "settlement_currency": "EUR",
                "actor_id": "u123",
                "actor_role": "advisor",
                "actor_channel": "web",
                "action": "draft",
            },
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        marker = "OD-"
        assert marker in html
        start = html.index(marker)
        draft_id = html[start:start + 9]

    db1.close()

    db2 = Database(str(db_path))
    stored = db2.get_order_draft(draft_id)
    assert stored is not None
    assert stored["payload"]["actor_id"] == "u123"
    assert stored["payload"]["actor_role"] == "advisor"
    assert stored["payload"]["actor_channel"] == "web"

    app2 = make_app(clients, pc, prices, order_database=db2)
    with app2.test_client() as c:
        response = c.get(f"/transactions/new?client_id=1&portfolio_id=1&order_draft_id={draft_id}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Orderstatus" in html
        assert "DRAFT" in html
        assert "u123" in html
        assert "advisor" in html
        assert "(web)" in html
        assert 'name="amount" id="amount" value="1000"' in html

    db2.close()


def test_order_drafts_monitoring_page_shows_summary_and_rows(tmp_path):
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    db_path = tmp_path / "order_monitoring.db"
    db = Database(str(db_path))
    db.upsert_order_draft(
        draft_id="OD-009999",
        portfolio_id=1,
        status="draft",
        payload={"template": "BUY", "product_id": 101, "actor_channel": "web"},
    )

    app = make_app(clients, pc, prices, order_database=db)
    with app.test_client() as c:
        response = c.get("/order-drafts?client_id=1&portfolio_id=1")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Order Draft Monitoring" in html
        assert "Statusoverzicht" in html
        assert "OD-009999" in html
        assert "draft" in html

    db.close()


def test_order_drafts_manual_cleanup_requires_confirmation(tmp_path):
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    db_path = tmp_path / "order_manual_cleanup_requires_confirm.db"
    db = Database(str(db_path))
    db.upsert_order_draft(
        draft_id="OD-001111",
        portfolio_id=1,
        status="draft",
        payload={"template": "BUY"},
    )

    app = make_app(clients, pc, prices, order_database=db)
    with app.test_client() as c:
        response = c.post(
            "/order-drafts",
            data={
                "client_id": "1",
                "portfolio_id": "1",
                "action": "cleanup",
                "retention_days": "1",
            },
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Bevestiging vereist" in html

    assert db.get_order_draft("OD-001111") is not None
    db.close()


def test_order_drafts_manual_cleanup_deletes_stale_drafts(tmp_path):
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)

    db_path = tmp_path / "order_manual_cleanup_success.db"
    db = Database(str(db_path))
    db.upsert_order_draft(
        draft_id="OD-001222",
        portfolio_id=1,
        status="draft",
        payload={"template": "BUY"},
        created_at="2000-01-01T00:00:00+00:00",
        updated_at="2000-01-01T00:00:00+00:00",
    )

    app = make_app(clients, pc, prices, order_database=db)
    with app.test_client() as c:
        response = c.post(
            "/order-drafts",
            data={
                "client_id": "1",
                "portfolio_id": "1",
                "action": "cleanup",
                "retention_days": "1",
                "cleanup_confirm": "1",
            },
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Opschonen voltooid" in html

    assert db.get_order_draft("OD-001222") is None
    db.close()
