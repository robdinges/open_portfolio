
# Zorg dat src/ in sys.path staat zodat open_portfolio altijd gevonden wordt
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from open_portfolio.web_app import make_app, create_demo_data
from open_portfolio.product_collection import ProductCollection

MENU_PATHS = [
    "/", "/holdings", "/transactions", "/clients", "/portfolios", "/accounts", "/instruments"
]

def setup_app():
    clients, products_list, prices = create_demo_data()
    pc = ProductCollection()
    for prod in products_list:
        pc.add_product(prod)
    app = make_app(None, pc, prices)
    return app, clients, products_list

def test_menu_pages_work():
    app, clients, _ = setup_app()
    with app.test_client() as c:
        for path in MENU_PATHS:
            resp = c.get(path)
            assert resp.status_code == 200, f"Failed on {path}"
            assert "Error" not in resp.get_data(as_text=True)

def test_client_switching_and_portfolio_buy():
    app, clients, products_list = setup_app()
    with app.test_client() as c:
        # Home, kies Client 2
        resp = c.get("/?client_id=" + str(clients[1].client_id))
        assert resp.status_code == 200
        assert clients[1].name in resp.get_data(as_text=True)
        # Switch terug naar Client 1
        resp = c.get("/?client_id=" + str(clients[0].client_id))
        assert resp.status_code == 200
        assert clients[0].name in resp.get_data(as_text=True)
        # Navigeer naar portefeuille Tech Amerika (bij Client 1)
        tech_portfolio = next((p for p in clients[0].portfolios if "Tech Amerika" in p.name), None)
        assert tech_portfolio is not None
        resp = c.get(f"/holdings?client_id={clients[0].client_id}&portfolio_id={tech_portfolio.portfolio_id}")
        assert resp.status_code == 200
        assert tech_portfolio.name in resp.get_data(as_text=True)
        # Buy order aanmaken voor bovenste positie
        holdings = getattr(tech_portfolio.securities_account, 'holdings', [])
        if holdings:
            product_id = holdings[0]["product"].instrument_id
        else:
            product_id = products_list[0].instrument_id
        resp = c.post(
            "/transactions/new",
            data={
                "client_id": clients[0].client_id,
                "portfolio_id": tech_portfolio.portfolio_id,
                "template": "BUY",
                "product_id": product_id,
                "amount": 1,
                "price": 1,
            },
            follow_redirects=True,
        )
        html = resp.get_data(as_text=True)
        assert resp.status_code == 200
        assert "Transaction" in html or "transactie" in html.lower()
        # Controleer dat geen echte foutmeldingen zichtbaar zijn (negeer CSS)
        body = html.split("<body>")[-1].split("</body>")[0] if "<body>" in html else html
        assert "error:" not in body.lower()
        assert "not found" not in body.lower()
        assert "internal server error" not in body.lower()
