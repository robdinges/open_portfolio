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

    def resolve_context(client_id=None, portfolio_id=None):
        selected_client = None
        if client_id:
            selected_client = next((c for c in clients if c.client_id == client_id), None)
        if selected_client is None:
            selected_client = clients[0]

        selected_portfolio = None
        if portfolio_id:
            selected_portfolio = next((p for p in selected_client.portfolios if p.portfolio_id == portfolio_id), None)
        if selected_portfolio is None and selected_client.portfolios:
            selected_portfolio = selected_client.portfolios[0]

        return selected_client, selected_portfolio

    def nav_query(selected_client, selected_portfolio):
        parts = []
        if selected_client:
            parts.append(f"client_id={selected_client.client_id}")
        if selected_portfolio:
            parts.append(f"portfolio_id={selected_portfolio.portfolio_id}")
        return f"?{'&'.join(parts)}" if parts else ""

    @app.route("/holdings")
    def holdings_page():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        return render_template(
            "holdings.html",
            selected_portfolio=selected_portfolio,
            selected_client=selected_client,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            format_currency=format_currency,
            active_page="holdings",
        )

    @app.route("/")
    def home():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        return render_template(
            "home.html",
            clients=clients,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            format_currency=format_currency,
            active_page="home",
        )

    @app.route("/transactions")
    def transactions():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        all_transactions = selected_portfolio.list_all_transactions() if selected_portfolio else []
        return render_template(
            "transactions.html",
            transactions=all_transactions,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            format_currency=format_currency,
            active_page="transactions",
        )

    # Verwijderd: dubbele lege functie new_transaction()
    @app.route("/transactions/new", methods=["GET", "POST"])
    def new_transaction():
        error = None
        success_message = None
        if request.method == "POST":
            selected_client_id = int(request.form.get("client_id", clients[0].client_id))
            selected_portfolio_id = int(request.form.get("portfolio_id", 0))
            selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
            selected_template = request.form.get("template")
            selected_product_id = request.form.get("product_id")
            return_to = request.form.get("return_to", "")

            if request.form.get("cancel") == "1":
                if return_to == "holdings":
                    return redirect(url_for("holdings_page", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
                return redirect(url_for("transactions", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))

            if request.form.get("save") == "1":
                try:
                    if selected_portfolio is None:
                        raise ValueError("Geen portefeuille geselecteerd")
                    template = TransactionTemplate[selected_template]
                    product_id = int(selected_product_id)
                    amount = float(request.form.get("amount", "0"))
                    price = float(request.form.get("price", "0"))

                    if amount <= 0:
                        raise ValueError("Aantal moet groter zijn dan 0")
                    if price < 0:
                        raise ValueError("Prijs kan niet negatief zijn")

                    if template == TransactionTemplate.SELL:
                        holding = next((
                            h for h in selected_portfolio.securities_account.holdings
                            if (
                                (isinstance(h, dict) and h.get("product") and h["product"].instrument_id == product_id)
                                or (not isinstance(h, dict) and getattr(getattr(h, "product", None), "instrument_id", None) == product_id)
                            )
                        ), None)
                        if isinstance(holding, dict):
                            available_amount = float(holding.get("amount", 0.0))
                        else:
                            available_amount = float(getattr(holding, "amount", 0.0)) if holding is not None else 0.0
                        if amount > available_amount:
                            raise ValueError("Onvoldoende positie voor verkoop")

                    tx_manager.create_and_execute_transaction(
                        transaction_date=date.today(),
                        portfolio_id=selected_portfolio.portfolio_id,
                        template=template,
                        portfolio=selected_portfolio,
                        product_collection=product_collection,
                        currency_prices=currency_prices,
                        product_id=product_id,
                        amount=amount,
                        price=price,
                    )
                    success_message = "Transactie succesvol opgeslagen"
                    if return_to == "holdings":
                        return redirect(url_for("holdings_page", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
                    return redirect(url_for("transactions", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
                except Exception as exc:
                    error = str(exc)
        else:
            selected_client_id = int(request.args.get("client_id", clients[0].client_id))
            fallback_portfolio_id = clients[0].portfolios[0].portfolio_id if clients and clients[0].portfolios else 0
            selected_portfolio_id = int(request.args.get("portfolio_id", fallback_portfolio_id))
            selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
            selected_template = request.args.get("template")
            selected_product_id = request.args.get("product_id")
        if selected_product_id:
            try:
                selected_product_id = int(selected_product_id)
            except Exception:
                pass
        if request.method != "POST":
            return_to = request.args.get("return_to", "")
        if request.method == "POST" and 'return_to' not in locals():
            return_to = request.form.get("return_to", "")
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
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            templates=[t for t in TransactionTemplate],
            products=product_collection.products,
            selected_client_id=selected_client_id,
            selected_portfolio_id=selected_portfolio_id,
            selected_template=selected_template,
            selected_product_id=selected_product_id,
            cash_accounts=cash_accounts,
            show_amount=True,
            amount_label=None,
            format_currency=format_currency,
            error=error,
            success_message=success_message,
            return_to=return_to,
            nav_query=nav_query(selected_client, selected_portfolio),
            active_page="transactions",
        )

    @app.route("/clients")
    def clients_page():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        return render_template(
            "home.html",
            clients=clients,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            format_currency=format_currency,
            active_page="home",
        )

    @app.route("/portfolios")
    def portfolios_page():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        return render_template(
            "home.html",
            clients=clients,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            format_currency=format_currency,
            active_page="home",
        )

    @app.route("/accounts")
    def accounts_page():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        accounts = []
        if selected_portfolio and hasattr(selected_portfolio, 'cash_accounts'):
            for (aid, curr, atype), acc in selected_portfolio.cash_accounts.items():
                acc.aid = aid
                acc.curr = curr
                acc.atype = atype
                acc.portfolio = selected_portfolio
                accounts.append(acc)
        return render_template(
            "accounts.html",
            accounts=accounts,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            format_currency=format_currency,
            active_page="accounts",
        )

    @app.route("/instruments")
    def instruments_page():
        selected_client_id = request.args.get("client_id", type=int)
        selected_portfolio_id = request.args.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        return render_template(
            "instruments.html",
            products=product_collection.products,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            active_page="instruments",
        )

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
