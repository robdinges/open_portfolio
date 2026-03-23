import pytest
from open_portfolio.web_app import make_app, create_demo_data
from open_portfolio.product_collection import ProductCollection


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
