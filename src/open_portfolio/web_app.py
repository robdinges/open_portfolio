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
from html import escape

try:
    from flask import Flask, request, redirect, url_for, render_template, flash
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
    return dataset['clients'], dataset['products'], dataset['prices']



# --- Currency formatting utility ---
import locale

def format_currency(amount, currency="EUR", symbol="€"):
    try:
        amount = float(amount)
    except Exception:
        return amount
    s = f"{amount:,.2f}"
    s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{symbol} {s}"

def make_app(client=None, product_collection=None, currency_prices=None):
    if Flask is None:
        raise RuntimeError("Flask is not installed. Please `pip install flask` to run the web UI.")

    # Initialiseer altijd closure-variabelen bovenaan
    if client is None or product_collection is None or currency_prices is None:
        clients, products_list, currency_prices = create_demo_data()
        product_collection = ProductCollection()
        for prod in products_list:
            product_collection.add_product(prod)
    else:
        clients = client if isinstance(client, list) else [client]

    app = Flask(__name__)
    tx_manager = TransactionManager()

    @app.route("/holdings")
    def holdings_page():
        selected_client_id = request.args.get("client_id", type=int)
        selected_client = None
        portfolios = []
        if selected_client_id:
            for c in clients:
                if c.client_id == selected_client_id:
                    selected_client = c
                    break
            if selected_client:
                portfolios = selected_client.portfolios
        else:
            # Verzamel alle portfolios van alle clients
            for c in clients:
                for p in c.portfolios:
                    portfolios.append(p)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_portfolio = None
        for p in portfolios:
            if selected_portfolio_id and p.portfolio_id == selected_portfolio_id:
                selected_portfolio = p
                break
        return render_template(
            "holdings.html",
            portfolios=portfolios,
            selected_portfolio=selected_portfolio,
            selected_client=selected_client,
            clients=clients,
            format_currency=format_currency
        )

    @app.route("/")
    def home():
        selected_client_id = request.args.get("client_id", type=int)
        selected_client = None
        if selected_client_id:
            for c in clients:
                if c.client_id == selected_client_id:
                    selected_client = c
                    break
        else:
            selected_client = clients[0]
        show_transaction_button = selected_client is not None
        return render_template(
            "home.html",
            clients=clients,
            selected_client=selected_client,
            format_currency=format_currency
        )

    @app.route("/transactions")
    def transactions():
        selected_client_id = request.args.get("client_id", type=int)
        selected_client = None
        if selected_client_id:
            for c in clients:
                if c.client_id == selected_client_id:
                    selected_client = c
                    break
        if not selected_client:
            selected_client = clients[0]
        all_transactions = []
        for p in selected_client.portfolios:
            if hasattr(p, 'transactions'):
                all_transactions.extend(p.transactions)
        return render_template("transactions.html", transactions=all_transactions, format_currency=format_currency, clients=clients, selected_client=selected_client)

    # Verwijderd: dubbele lege functie new_transaction()
    @app.route("/transactions/new", methods=["GET", "POST"])
    def new_transaction():
        if request.method == "POST":
            selected_client_id = int(request.form.get("client_id", clients[0].client_id))
            selected_client = next((c for c in clients if c.client_id == selected_client_id), clients[0])
            selected_portfolio_id = int(request.form.get("portfolio_id", selected_client.portfolios[0].portfolio_id if selected_client.portfolios else 0))
            selected_template = request.form.get("template")
            selected_product_id = request.form.get("product_id")
        else:
            selected_client_id = clients[0].client_id
            selected_client = clients[0]
            selected_portfolio_id = selected_client.portfolios[0].portfolio_id if selected_client.portfolios else 0
            selected_template = None
            selected_product_id = None
        selected_portfolio = None
        for p in selected_client.portfolios:
            if p.portfolio_id == selected_portfolio_id:
                selected_portfolio = p
                break
        cash_accounts = []
        if selected_portfolio and hasattr(selected_portfolio, 'cash_accounts'):
            for (aid, curr, atype), acc in selected_portfolio.cash_accounts.items():
                acc.aid = aid
                acc.curr = curr
                acc.atype = atype
                cash_accounts.append(acc)
        return render_template(
            "transaction_form.html",
            clients=clients,
            portfolios=selected_client.portfolios,
            templates=[t for t in TransactionTemplate],
            products=product_collection.products,
            selected_client_id=selected_client_id,
            selected_portfolio_id=selected_portfolio_id,
            selected_template=selected_template,
            selected_product_id=selected_product_id,
            cash_accounts=cash_accounts,
            show_amount=True,
            amount_label=None,
            format_currency=format_currency
        )

    @app.route("/clients")
    def clients_page():
        return render_template("clients.html", clients=clients)

    @app.route("/portfolios")
    def portfolios_page():
        # Verzamel alle portefeuilles van deze client
        # Zorg dat elke portfolio een client attribuut heeft
        selected_client_id = request.args.get("client_id", type=int)
        selected_client = None
        portfolios = []
        if selected_client_id:
            for c in clients:
                if c.client_id == selected_client_id:
                    selected_client = c
                    break
            if selected_client:
                portfolios = selected_client.portfolios
                for p in portfolios:
                    if not hasattr(p, 'client'):
                        p.client = selected_client
        else:
            # Verzamel alle portfolios van alle clients
            for c in clients:
                for p in c.portfolios:
                    if not hasattr(p, 'client'):
                        p.client = c
                    portfolios.append(p)
        return render_template("portfolios.html", portfolios=portfolios, clients=clients, selected_client=selected_client)

    @app.route("/accounts")
    def accounts_page():
        # Verzamel alle cash accounts van alle portefeuilles
        selected_client_id = request.args.get("client_id", type=int)
        selected_client = None
        if selected_client_id:
            for c in clients:
                if c.client_id == selected_client_id:
                    selected_client = c
                    break
        accounts = []
        source_clients = [selected_client] if selected_client else clients
        for cl in source_clients:
            for p in cl.portfolios:
                if hasattr(p, 'cash_accounts'):
                    for (aid, curr, atype), acc in p.cash_accounts.items():
                        acc.aid = aid
                        acc.curr = curr
                        acc.atype = atype
                        acc.portfolio = p
                        accounts.append(acc)
        return render_template("accounts.html", accounts=accounts, clients=clients, selected_client=selected_client, format_currency=format_currency)

    @app.route("/instruments")
    def instruments_page():
        return render_template("instruments.html", products=product_collection.products)

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
