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


BASE_STYLES = """
<style>
    :root {
        color-scheme: light;
        --bg: #f5f7fb;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --text: #0f172a;
        --text-muted: #475569;
        --border: #dbe3ee;
        --primary: #2563eb;
        --primary-hover: #1d4ed8;
        --success-bg: #ecfdf3;
        --success-text: #166534;
        --success-border: #bbf7d0;
        --error-bg: #fef2f2;
        --error-text: #991b1b;
        --error-border: #fecaca;
    }

    * { box-sizing: border-box; }

    body {
        margin: 0;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: radial-gradient(circle at top right, #e2e8f0 0%, #f5f7fb 38%, #f5f7fb 100%);
        color: var(--text);
    }

    .page {
        max-width: 1040px;
        margin: 0 auto;
        padding: 2rem 1rem 3rem;
    }

    .hero {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }

    .hero h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .hero p {
        margin: 0.35rem 0 0;
        color: var(--text-muted);
    }

    .stack {
        display: grid;
        gap: 1rem;
    }

    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1rem;
    }

    .card h2,
    .card h3 {
        margin: 0 0 0.8rem;
        font-size: 1.05rem;
        letter-spacing: -0.01em;
    }

    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 0.9rem;
    }

    .field {
        display: grid;
        gap: 0.4rem;
    }

    .field label {
        font-weight: 600;
        font-size: 0.92rem;
    }

    input,
    select {
        width: 100%;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--surface-soft);
        color: var(--text);
        padding: 0.62rem 0.72rem;
        font-size: 0.95rem;
    }

    input:focus,
    select:focus {
        border-color: var(--primary);
        outline: none;
        background: #fff;
    }

    .actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
        gap: 0.8rem;
        flex-wrap: wrap;
    }

    .button,
    .button-secondary {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.92rem;
        padding: 0.6rem 0.95rem;
        text-decoration: none;
        display: inline-block;
    }

    .button {
        border: none;
        cursor: pointer;
        background: var(--primary);
        color: #fff;
    }

    .button:hover {
        background: var(--primary-hover);
    }

    .button-secondary {
        border: 1px solid var(--border);
        color: var(--text);
        background: #fff;
    }

    .alert {
        border: 1px solid;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        margin-bottom: 1rem;
        font-size: 0.95rem;
    }

    .alert.success {
        background: var(--success-bg);
        color: var(--success-text);
        border-color: var(--success-border);
    }

    .alert.error {
        background: var(--error-bg);
        color: var(--error-text);
        border-color: var(--error-border);
    }

    .list {
        margin: 0;
        padding-left: 1.15rem;
        color: var(--text-muted);
    }

    .list li {
        margin: 0.35rem 0;
    }

    .account {
        margin: 0;
        white-space: pre-wrap;
        color: var(--text-muted);
        font-size: 0.92rem;
        background: var(--surface-soft);
        border-radius: 10px;
        border: 1px solid var(--border);
        padding: 0.7rem;
    }
</style>
"""


def create_demo_data():
    """Use realistic dataset instead of minimal hardcoded demo data."""
    dataset = create_realistic_dataset()
    # Return first client with all products and prices
    # For simplicity, display first client in web UI
    return dataset['clients'][0], dataset['products'], dataset['prices']



# --- Currency formatting utility ---
import locale
def format_currency(amount, currency="EUR", symbol="€"):
    try:
        locale.setlocale(locale.LC_ALL, "nl_NL.UTF-8")
    except Exception:
        locale.setlocale(locale.LC_ALL, "")
    # Format with comma decimal, dot thousand separator, two decimals
    try:
        formatted = locale.currency(amount, symbol, grouping=True)
        # locale.currency gives e.g. € 1.234,56
        return formatted
    except Exception:
        # fallback
        return f"{symbol} {amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

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
        html = [
            "<!doctype html>",
            "<html lang=\"nl\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "<title>OpenPortfolio Demo</title>",
            BASE_STYLES,
            "<style> .valuta {{ text-align: right; font-variant-numeric: tabular-nums; min-width: 7em; }} .code-desc {{ font-size: 0.97em; color: var(--text-muted); }} </style>",
            "</head>",
            "<body><main class=\"page\">",
            "<section class=\"hero\">",
            "<div>",
            "<h1>OpenPortfolio - Demo</h1>",
            f"<p>Client: <span class=\"code-desc\">{escape(client.client_id)} – {escape(client.name)}</span></p>",
            "</div>",
            "<a class=\"button\" href=\"/transaction/new\">Nieuwe transactie</a>",
            "</section>",
            "<section class=\"card stack\">",
            "<h2>Portefeuilles</h2>",
            "<table style='width:100%; border-spacing:0; border-collapse:separate;'>",
            "<thead><tr><th style='text-align:left'>ID & Omschrijving</th><th style='text-align:left'>Rekeningen</th></tr></thead><tbody>"
        ]
        for p in client.portfolios:
            html.append("<tr>")
            html.append(f"<td><span class='code-desc'>{p.portfolio_id} – {escape(p.name)}</span></td>")
            html.append("<td><table style='width:auto;'><thead><tr><th>ID</th><th>Valuta</th><th>Type</th><th>Saldo</th></tr></thead><tbody>")
            for (aid, curr, atype), acc in p.cash_accounts.items():
                html.append("<tr>")
                html.append(f"<td>{aid}</td><td>{curr}</td><td>{atype.name}</td><td class='valuta'>{format_currency(acc.balance, curr, '€' if curr=='EUR' else curr)}</td>")
                html.append("</tr>")
            html.append("</tbody></table></td>")
            html.append("</tr>")
        html.append("</tbody></table>")
        html.append("</section>")
        html.append("</main></body></html>")
        return "\n".join(html)

    @app.route("/transaction/new", methods=["GET", "POST"])
    def new_transaction():
        message = None
        portfolio_summary = None
        if request.method == "POST":
            try:
                portfolio_id = int(request.form.get("portfolio_id"))
                template = TransactionTemplate[request.form.get("template")]
                product_id = int(request.form.get("product_id")) if request.form.get("product_id") else None
                amount = float(request.form.get("amount"))
                price = float(request.form.get("price"))
                portfolio = next(p for p in client.portfolios if p.portfolio_id == portfolio_id)
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
                message = ("success", "Transactie succesvol uitgevoerd.")
            except Exception as e:
                message = ("error", f"Fout: {e}")

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

        portfolios_options = "".join(
            f"<option value=\"{p.portfolio_id}\">{p.portfolio_id} – {escape(p.name)}</option>" for p in client.portfolios
        )
        templates_options = "".join(f"<option>{t.name}</option>" for t in TransactionTemplate)
        products_options = "".join(
            f"<option value=\"{pid}\">{pid} – {escape(prod.description)}</option>" for pid, prod in product_collection.products.items()
        )

        message_html = ""
        if message:
            message_html = f"<div class=\"alert {message[0]}\">{escape(message[1])}</div>"

        summary_html = ""
        if portfolio_summary:
            summary_html = "<section class=\"stack\">"
            summary_html += "<article class=\"card\"><h3>Laatste 5 transacties</h3><table class=\"list\"><thead><tr><th>Datum</th><th>#</th><th>Type</th><th>Product</th><th>Bedrag</th></tr></thead><tbody>"
            for tx in portfolio_summary["last_transactions"]:
                summary_html += (
                    f"<tr><td>{escape(str(tx['transaction_date']))}</td>"
                    f"<td>{escape(str(tx['transaction_number']))}</td>"
                    f"<td>{escape(str(tx.get('template', '')))}</td>"
                    f"<td>{escape(str(tx.get('product_id', '')))}</td>"
                    f"<td class='valuta'>{format_currency(tx.get('amount', 0))}</td></tr>"
                )
            summary_html += "</tbody></table></article>"

            summary_html += "<article class=\"card\"><h3>Posities</h3><table class=\"list\"><thead><tr><th>Product</th><th>Aantal</th><th>Prijs</th><th>Waarde</th></tr></thead><tbody>"
            for h in portfolio_summary["holdings"]:
                summary_html += (
                    f"<tr><td>{escape(str(h['product_id']))}</td>"
                    f"<td class='valuta'>{h['amount']:.2f}</td>"
                    f"<td class='valuta'>{format_currency(h['price'])}</td>"
                    f"<td class='valuta'>{format_currency(h['value'])}</td></tr>"
                )
            summary_html += "</tbody></table></article>"

            summary_html += "<article class=\"card\"><h3>Kasposities</h3><table class=\"list\"><thead><tr><th>Valuta</th><th>Saldo</th></tr></thead><tbody>"
            for cb in portfolio_summary["cash_balances"]:
                summary_html += f"<tr><td>{escape(str(cb['currency']))}</td><td class='valuta'>{format_currency(cb['balance'], cb['currency'], '€' if cb['currency']=='EUR' else cb['currency'])}</td></tr>"
            summary_html += "</tbody></table></article></section>"

        form = f"""
        <!doctype html>
        <html lang=\"nl\">
        <head>
          <meta charset=\"utf-8\">
          <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
          <title>Nieuwe transactie</title>
          {BASE_STYLES}
          <style>
            input[type=number] {{ width: 8em; }}
            select {{ width: 18em; }}
            .valuta {{ text-align: right; font-variant-numeric: tabular-nums; min-width: 7em; }}
            .code-desc {{ font-size: 0.97em; color: var(--text-muted); }}
          </style>
        </head>
        <body>
          <main class=\"page stack\">
            <section class=\"hero\">
              <div>
                <h1>Nieuwe transactie</h1>
                <p>Voer een transactie in en verwerk deze direct.</p>
              </div>
              <a class=\"button-secondary\" href=\"/\">Terug naar overzicht</a>
            </section>
            <section class=\"card\">
              {message_html}
              <form method=\"post\" class=\"stack\">
                <div class=\"grid\">
                  <div class=\"field\">
                    <label for=\"portfolio_id\">Portefeuille</label>
                    <select id=\"portfolio_id\" name=\"portfolio_id\">{portfolios_options}</select>
                  </div>
                  <div class=\"field\">
                    <label for=\"template\">Type</label>
                    <select id=\"template\" name=\"template\">{templates_options}</select>
                  </div>
                  <div class=\"field\">
                    <label for=\"product_id\">Product</label>
                    <select id=\"product_id\" name=\"product_id\"><option value=\"\">(geen)</option>{products_options}</select>
                  </div>
                </div>
                <div class=\"grid\">
                  <div class=\"field\">
                    <label for=\"amount\">Aantal</label>
                    <input id=\"amount\" name=\"amount\" type=\"number\" step=\"any\" required placeholder=\"0,00\" style=\"width:8em;\" />
                  </div>
                  <div class=\"field\">
                    <label for=\"price\">Prijs</label>
                    <input id=\"price\" name=\"price\" type=\"number\" step=\"any\" required placeholder=\"0,00\" style=\"width:8em;\" />
                  </div>
                </div>
                <div class=\"actions\">
                  <span style=\"color: var(--text-muted); font-size: 0.9rem;\">Transactiedatum: vandaag</span>
                  <button class=\"button\" type=\"submit\">Uitvoeren</button>
                </div>
              </form>
            </section>
            {summary_html}
          </main>
        </body>
        </html>
        """

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
