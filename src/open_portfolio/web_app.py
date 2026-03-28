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
    from flask import Flask, request, redirect, url_for, render_template
except Exception as e:  # pragma: no cover - runtime dependency
    Flask = None  # type: ignore

from .product_collection import ProductCollection
from .transactions import TransactionManager
from .enums import TransactionTemplate
from .sample_data import create_realistic_dataset





def create_demo_data():
    """Use realistic dataset instead of minimal hardcoded demo data."""
    dataset = create_realistic_dataset()
    return dataset['clients'], dataset['products'], dataset['prices']



# --- Currency formatting utility ---

def format_currency(amount, currency="EUR", symbol="€"):
    symbols = {
        "EUR": "EUR",
        "USD": "USD",
        "GBP": "GBP",
        "CHF": "CHF",
    }
    try:
        amount = float(amount)
    except Exception:
        return amount
    s = f"{amount:,.2f}"
    s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    display_symbol = symbols.get(currency, symbol)
    return f"{display_symbol} {s}"

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
            valuation_date=date.today(),
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
        # Sorteer transacties op datum, nieuwste bovenaan
        all_transactions = sorted(all_transactions, key=lambda tx: tx.get('date', tx.get('transaction_date', '')), reverse=True)
        return render_template(
            "transactions.html",
            transactions=all_transactions,
            product_collection=product_collection,
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

        def parse_decimal(value: str, field_name: str) -> float:
            text = (value or "").strip()
            if not text:
                raise ValueError(f"{field_name} is verplicht")
            text = text.replace(" ", "").replace(",", ".")
            try:
                return float(text)
            except ValueError as exc:
                raise ValueError(f"{field_name} heeft geen geldig getal") from exc

        def parse_optional_decimal(value: str) -> float | None:
            text = (value or "").strip()
            if not text:
                return None
            text = text.replace(" ", "").replace(",", ".")
            return float(text)

        def parse_tx_date(raw_value: str | None) -> date:
            text = (raw_value or "").strip()
            if not text:
                return date.today()
            parts = text.split("-")
            if len(parts) != 3:
                raise ValueError("Transactiedatum heeft ongeldig formaat (gebruik YYYY-MM-DD)")
            try:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            except ValueError as exc:
                raise ValueError("Transactiedatum is ongeldig") from exc

        def get_fx(from_currency: str, to_currency: str) -> float:
            if from_currency == to_currency:
                return 1.0
            try:
                return float(currency_prices.get_latest_price(from_currency, to_currency))
            except Exception:
                try:
                    return 1.0 / float(currency_prices.get_latest_price(to_currency, from_currency))
                except Exception as exc:
                    raise ValueError(f"Geen wisselkoers beschikbaar voor {from_currency}/{to_currency}") from exc

        def get_position_map(selected_portfolio):
            result = {}
            if not selected_portfolio or not selected_portfolio.securities_account:
                return result
            for holding in selected_portfolio.securities_account.holdings:
                if isinstance(holding, dict) and holding.get("product"):
                    pid = holding["product"].instrument_id
                    amount = float(holding.get("amount", 0.0))
                else:
                    pid = getattr(getattr(holding, "product", None), "instrument_id", None)
                    amount = float(getattr(holding, "amount", 0.0))
                if pid is not None:
                    result[pid] = amount
            return result

        def build_settlement_options(selected_portfolio, product):
            options = []
            locked = False
            default_currency = getattr(selected_portfolio, "default_currency", "EUR") if selected_portfolio else "EUR"
            if not selected_portfolio or not product:
                return options, locked

            cash_by_currency = {}
            for (_, curr, atype), account in selected_portfolio.cash_accounts.items():
                if atype.name == "CASH" and curr not in cash_by_currency:
                    cash_by_currency[curr] = account

            issue_currency = product.issue_currency
            if issue_currency == default_currency:
                account = cash_by_currency.get(default_currency)
                if account:
                    options.append({"currency": default_currency, "balance": account.balance})
                locked = True
                return options, locked

            issue_account = cash_by_currency.get(issue_currency)
            default_account = cash_by_currency.get(default_currency)
            if issue_account:
                options.append({"currency": issue_currency, "balance": issue_account.balance})
            if default_account and default_currency != issue_currency:
                options.append({"currency": default_currency, "balance": default_account.balance})
            return options, locked

        def is_multiple_of_unit(value: float, unit: float) -> bool:
            if unit <= 0:
                return True
            quotient = value / unit
            return abs(round(quotient) - quotient) <= 1e-9

        def get_latest_price_for_date(product, tx_date: date) -> float:
            price = product.get_price(tx_date)
            if price is None:
                raise ValueError("Geen koers beschikbaar op of voor transactiedatum")
            return float(price)

        def calculate_cost(amount: float, price: float) -> float:
            return 0.01 * amount * price

        def product_kind(product) -> str:
            kind = getattr(getattr(product, "type", None), "name", "")
            return kind.lower() if kind else "unknown"

        def to_execution_price(product, displayed_price: float) -> float:
            if product_kind(product) == "bond":
                return displayed_price / 100.0
            return displayed_price

        if request.method == "POST":
            selected_client_id = int(request.form.get("client_id", clients[0].client_id))
            selected_portfolio_id = int(request.form.get("portfolio_id", 0))
            selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
            selected_template = request.form.get("template") or "BUY"
            selected_order_type = request.form.get("order_type") or "MARKET"
            selected_product_id = request.form.get("product_id")
            selected_settlement_currency = request.form.get("settlement_currency")
            entered_amount = request.form.get("amount", "")
            entered_price = request.form.get("price", "")
            entered_tx_date = request.form.get("transaction_date", date.today().isoformat())
            return_to = request.form.get("return_to", "")
        else:
            selected_client_id = int(request.args.get("client_id", clients[0].client_id))
            fallback_portfolio_id = clients[0].portfolios[0].portfolio_id if clients and clients[0].portfolios else 0
            selected_portfolio_id = int(request.args.get("portfolio_id", fallback_portfolio_id))
            selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
            selected_template = request.args.get("template") or "BUY"
            selected_order_type = request.args.get("order_type") or "MARKET"
            selected_product_id = request.args.get("product_id")
            selected_settlement_currency = request.args.get("settlement_currency")
            entered_amount = request.args.get("amount", "")
            entered_price = request.args.get("price", "")
            entered_tx_date = request.args.get("transaction_date", date.today().isoformat())
            return_to = request.args.get("return_to", "")

        if selected_product_id:
            try:
                selected_product_id = int(selected_product_id)
            except Exception:
                selected_product_id = None

        # Keep backend state aligned with the first visible instrument so
        # settlement account options are always determinable.
        if selected_product_id is None and product_collection.products:
            selected_product_id = sorted(product_collection.products.keys())[0]

        product = product_collection.search_product_id(selected_product_id) if selected_product_id else None
        position_by_product = get_position_map(selected_portfolio)
        current_position = position_by_product.get(selected_product_id, 0.0) if selected_product_id else 0.0

        settlement_options, settlement_locked = build_settlement_options(selected_portfolio, product)
        allowed_settlement_currencies = [opt["currency"] for opt in settlement_options]
        if not selected_settlement_currency and allowed_settlement_currencies:
            selected_settlement_currency = allowed_settlement_currencies[0]
        if selected_settlement_currency not in allowed_settlement_currencies and allowed_settlement_currencies:
            selected_settlement_currency = allowed_settlement_currencies[0]

        selected_settlement_balance = None
        for opt in settlement_options:
            if opt["currency"] == selected_settlement_currency:
                selected_settlement_balance = opt["balance"]
                break

        current_product_kind = product_kind(product) if product else "unknown"
        is_bond = current_product_kind == "bond"
        amount_label = "Nominale waarde" if is_bond else "Aantal"
        amount_unit = product.smallest_trading_unit if product else None
        minimum_order_size = product.minimum_purchase_value if product else None
        amount_suffix = product.issue_currency if is_bond and product else ""

        show_price_input = selected_order_type == "LIMIT"
        limit_suffix = "%" if is_bond and selected_order_type == "LIMIT" else (product.issue_currency if selected_order_type == "LIMIT" and product else "")

        estimated_trade = None
        estimated_cost = None
        estimated_accrued = None
        estimated_total = None
        used_price = None

        if request.method == "POST" and request.form.get("cancel") == "1":
            if return_to == "holdings":
                return redirect(url_for("holdings_page", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
            return redirect(url_for("transactions", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))

        if request.method == "POST" and request.form.get("save") == "1":
            try:
                if selected_portfolio is None:
                    raise ValueError("Geen portefeuille geselecteerd")
                if product is None:
                    raise ValueError("Instrument niet gevonden")
                if selected_template not in {"BUY", "SELL"}:
                    raise ValueError("Ongeldige transactiesoort")
                if selected_order_type not in {"MARKET", "LIMIT"}:
                    raise ValueError("Ongeldig ordertype")

                tx_date = parse_tx_date(entered_tx_date)
                amount = parse_decimal(entered_amount, amount_label)
                if amount <= 0:
                    raise ValueError(f"{amount_label} moet groter zijn dan 0")

                template = TransactionTemplate[selected_template]
                if template == TransactionTemplate.SELL and amount > current_position:
                    raise ValueError("Onvoldoende positie voor verkoop")

                if amount_unit and not is_multiple_of_unit(amount, float(amount_unit)):
                    raise ValueError(f"{amount_label} moet een veelvoud zijn van handelseenheid {amount_unit}")
                if template == TransactionTemplate.BUY and minimum_order_size and amount < float(minimum_order_size):
                    raise ValueError(f"{amount_label} moet minimaal {minimum_order_size} zijn")

                if selected_order_type == "LIMIT":
                    limit_price = parse_decimal(entered_price, "Limiet")
                    if limit_price <= 0:
                        raise ValueError("Limiet moet groter zijn dan 0")
                    displayed_price = limit_price
                else:
                    displayed_price = get_latest_price_for_date(product, tx_date)
                    entered_price = f"{displayed_price:.6f}".rstrip("0").rstrip(".")

                price = to_execution_price(product, displayed_price)

                if selected_settlement_currency not in allowed_settlement_currencies:
                    raise ValueError("Ongeldige afrekenrekening gekozen")
                if not selected_settlement_currency:
                    raise ValueError("Geen afrekenrekening beschikbaar voor deze order")

                exchange_rate = get_fx(product.issue_currency, selected_settlement_currency)

                trade_amount_settlement = amount * price * exchange_rate
                cost_settlement = calculate_cost(amount, price) * exchange_rate
                accrued_settlement = 0.0
                if is_bond:
                    accrued_settlement = product.calculate_accrued_interest(amount, tx_date) * exchange_rate

                if template == TransactionTemplate.BUY:
                    estimated_cash_impact = trade_amount_settlement + cost_settlement + max(accrued_settlement, 0)
                    if selected_settlement_balance is not None and estimated_cash_impact > float(selected_settlement_balance):
                        raise ValueError("Onvoldoende beschikbaar saldo op gekozen rekening")

                tx_manager.create_and_execute_transaction(
                    transaction_date=tx_date,
                    portfolio_id=selected_portfolio.portfolio_id,
                    template=template,
                    portfolio=selected_portfolio,
                    product_collection=product_collection,
                    currency_prices=currency_prices,
                    product_id=product.instrument_id,
                    amount=amount,
                    price=price,
                    transaction_currency=selected_settlement_currency,
                    exchange_rate=exchange_rate,
                    settlement_currency=selected_settlement_currency,
                )

                success_message = "Transactie succesvol opgeslagen"
                return redirect(url_for("transactions", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
            except Exception as exc:
                error = str(exc)

        try:
            if product and selected_settlement_currency:
                tx_date_preview = parse_tx_date(entered_tx_date)
                amount_preview = parse_optional_decimal(entered_amount)
                if amount_preview and amount_preview > 0:
                    if selected_order_type == "MARKET":
                        used_price = get_latest_price_for_date(product, tx_date_preview)
                    else:
                        limit_preview = parse_optional_decimal(entered_price)
                        used_price = limit_preview if limit_preview is not None else None

                    if used_price is not None and used_price > 0:
                        execution_price = to_execution_price(product, used_price)
                        fx = get_fx(product.issue_currency, selected_settlement_currency)
                        estimated_trade = amount_preview * execution_price * fx
                        estimated_cost = calculate_cost(amount_preview, execution_price) * fx
                        if is_bond:
                            estimated_accrued = product.calculate_accrued_interest(amount_preview, tx_date_preview) * fx
                        else:
                            estimated_accrued = 0.0

                        if selected_template == "SELL":
                            estimated_total = estimated_trade - estimated_cost + (estimated_accrued or 0.0)
                        else:
                            estimated_total = estimated_trade + estimated_cost + (estimated_accrued or 0.0)
        except Exception:
            # Preview should never block rendering.
            pass

        products_by_type = {"bond": [], "stock": [], "option": [], "fund": [], "other": []}
        for pid, prod in sorted(product_collection.products.items(), key=lambda item: item[1].description.lower()):
            kind = product_kind(prod)
            if kind not in products_by_type:
                kind = "other"
            products_by_type[kind].append((pid, prod))

        return render_template(
            "transaction_form.html",
            clients=clients,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            templates=[TransactionTemplate.BUY, TransactionTemplate.SELL],
            products=product_collection.products,
            products_by_type=products_by_type,
            selected_client_id=selected_client_id,
            selected_portfolio_id=selected_portfolio_id,
            selected_template=selected_template,
            selected_order_type=selected_order_type,
            selected_product_id=selected_product_id,
            amount=entered_amount,
            price=entered_price,
            transaction_date=entered_tx_date,
            settlement_options=settlement_options,
            selected_settlement_currency=selected_settlement_currency,
            selected_settlement_balance=selected_settlement_balance,
            settlement_locked=settlement_locked,
            current_position=current_position,
            position_by_product=position_by_product,
            amount_label=amount_label,
            amount_suffix=amount_suffix,
            amount_unit=amount_unit,
            minimum_order_size=minimum_order_size,
            show_price_input=show_price_input,
            limit_suffix=limit_suffix,
            current_product_kind=current_product_kind,
            used_price=used_price,
            estimated_trade=estimated_trade,
            estimated_cost=estimated_cost,
            estimated_accrued=estimated_accrued,
            estimated_total=estimated_total,
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
