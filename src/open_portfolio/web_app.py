"""Minimal web frontend for OpenPortfolio.

Run with:

PYTHONPATH=src python3 -m open_portfolio.web_app

The module tries to import Flask and will show a helpful error if it's
not installed. The web UI is intentionally tiny: an overview page and a
form to submit a BUY/SELL transaction.
"""
from __future__ import annotations
import sys
from datetime import date

try:
    from flask import Flask, request, redirect, url_for
except Exception as e:  # pragma: no cover - runtime dependency
    Flask = None  # type: ignore

from .clients import Client
from .product_collection import ProductCollection
from .transactions import TransactionManager
from .enums import TransactionTemplate
from .products import Stock, Bond
from .prices import CurrencyPrices
from .sample_data import create_realistic_dataset


def create_demo_data():
    """Use realistic dataset instead of minimal hardcoded demo data."""
    dataset = create_realistic_dataset()
    # Return first client with all products and prices
    # For simplicity, display first client in web UI
    return dataset['clients'][0], dataset['products'], dataset['prices']


def make_app(client=None, product_collection=None, currency_prices=None):
    if Flask is None:
        raise RuntimeError("Flask is not installed. Please `pip install flask` to run the web UI.")

    app = Flask(__name__)
    tx_manager = TransactionManager()

    if client is None or product_collection is None or currency_prices is None:
        client, products_list, currency_prices = create_demo_data()
        # Rebuild ProductCollection from products list
        product_collection = ProductCollection()
        for prod in products_list:
            product_collection.add_product(prod)

    @app.route("/")
    def index():
        # simple HTML overview
        # use bootstrap container for basic styling
        html = [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "<link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">",
            "<title>OpenPortfolio Demo</title>",
            "</head>",
            "<body><div class=\"container py-4\">",
            "<h1>OpenPortfolio - Localhost Demo</h1>",
        ]
        html.append("<h2>Portfolios</h2>")
        for p in client.portfolios:
            html.append(f"<h3>Portfolio {p.portfolio_id} - {p.name}</h3>")
            html.append("<pre>Accounts:\n")
            for (aid, curr, atype), acc in p.cash_accounts.items():
                html.append(f"{aid} {curr} {atype.name} balance={acc.balance}\n")
            html.append("</pre>")
        html.append('<p><a class="btn btn-secondary" href="/transaction/new">New Transaction</a></p>')
        html.append("</div></body></html>")
        return "\n".join(html)

    @app.route("/transaction/new", methods=["GET", "POST"])
    def new_transaction():
        message = None
        portfolio_summary = None
        # handle POST submissions and compute portfolio summary
        if request.method == "POST":
            try:
                portfolio_id = int(request.form.get("portfolio_id"))
                template = TransactionTemplate[request.form.get("template")]
                product_id = int(request.form.get("product_id")) if request.form.get("product_id") else None
                amount = float(request.form.get("amount"))
                price = float(request.form.get("price"))
                portfolio = next(p for p in client.portfolios if p.portfolio_id == portfolio_id)
                # attempt to create & execute
                tx_manager.create_and_execute_transaction(
                    transaction_date=date.today(),
                    portfolio_id=portfolio_id,
                    template=template,
                    portfolio=portfolio,
                    product_collection=product_collection,
                    currency_prices=currency_prices,
                    product_id=product_id,
                    amount=amount,
                    price=price,
                )
                message = "<div class=\"alert alert-success\">Transaction executed successfully.</div>"
            except Exception as e:
                message = f"<div class=\"alert alert-danger\">Error: {e}</div>"

            # build a small summary for the affected portfolio
            try:
                all_txs = portfolio.list_all_transactions()
                all_txs.sort(key=lambda tx: tx.get("transaction_number", 0))
                last5 = all_txs[-5:]

                holdings_raw = portfolio.securities_account.get_holding_values(date.today())
                holdings = [
                    {"product_id": h[2], "amount": h[3], "price": h[4], "value": h[1]}
                    for h in holdings_raw
                ]

                cash_balances = [
                    {"currency": acc.currency, "balance": acc.get_balance(date.today())}
                    for acc in portfolio.cash_accounts.values()
                ]

                portfolio_summary = {
                    "last_transactions": last5,
                    "holdings": holdings,
                    "cash_balances": cash_balances,
                    "portfolio_id": portfolio_id,
                }
            except NameError:
                portfolio_summary = None

        # render form for GET or after POST
        portfolios_options = "".join(
            f"<option value=\"{p.portfolio_id}\">{p.portfolio_id}</option>" for p in client.portfolios
        )
        templates_options = "".join(f"<option>{t.name}</option>" for t in TransactionTemplate)
        products_options = "".join(
            f"<option value=\"{pid}\">{pid} - {prod.description}</option>" for pid, prod in product_collection.products.items()
        )
        form = f"""
        <!doctype html>
        <html lang=\"en\">
        <head>
          <meta charset=\"utf-8\">
          <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
          <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
          <title>New Transaction</title>
        </head>
        <body><div class=\"container py-4\">{message or ""}
        <h1>New Transaction</h1>
        <form method=\"post\">
          <div class=\"mb-3\">Portfolio: <select class=\"form-select\" name=\"portfolio_id\">{portfolios_options}</select></div>
          <div class=\"mb-3\">Type: <select class=\"form-select\" name=\"template\">{templates_options}</select></div>
          <div class=\"mb-3\">Product ID: <select class=\"form-select\" name=\"product_id\"><option value=\"\">(none)</option>{products_options}</select></div>
          <div class=\"mb-3\">Amount: <input class=\"form-control\" name=\"amount\" /></div>
          <div class=\"mb-3\">Price: <input class=\"form-control\" name=\"price\" /></div>
          <button class=\"btn btn-primary\" type=\"submit\">Execute</button>
        </form>
        <p class=\"mt-3\"><a href=\"/\">Back</a></p>
        </div></body>
        </html>
        """
        # if we computed a summary, append it to the form output
        if portfolio_summary:
            form += "<hr><h2>Portfolio Summary</h2>"
            form += "<h3>Last 5 Transactions</h3><ul>"
            for tx in portfolio_summary["last_transactions"]:
                form += (
                    f"<li>{tx['transaction_date']} # {tx['transaction_number']} {tx.get('template','')} "
                    f"{tx.get('product_id','')} {tx.get('amount','')}</li>"
                )
            form += "</ul>"

            form += "<h3>Positions</h3><ul>"
            for h in portfolio_summary["holdings"]:
                form += (
                    f"<li>Product {h['product_id']}: {h['amount']} units @ {h['price']} = {h['value']}</li>"
                )
            form += "</ul>"

            form += "<h3>Cash Balances</h3><ul>"
            for cb in portfolio_summary["cash_balances"]:
                form += f"<li>{cb['currency']}: {cb['balance']}</li>"
            form += "</ul>"

        return form

    return app


def run(host="127.0.0.1", port=5000):
    if Flask is None:
        print("Flask is not installed. Install with: pip install flask", file=sys.stderr)
        return
    client, products_list, currency_prices = create_demo_data()
    # Rebuild ProductCollection from products list
    product_collection = ProductCollection()
    for prod in products_list:
        product_collection.add_product(prod)
    app = make_app(client, product_collection, currency_prices)
    app.run(host=host, port=port)


if __name__ == "__main__":
    # allow module invocation
    run()
