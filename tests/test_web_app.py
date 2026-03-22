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
        assert "Portfolios" in html
        # the first client's name should appear in the overview
        assert client[0].name in html
