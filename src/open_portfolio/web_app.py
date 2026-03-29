"""Minimal web frontend for OpenPortfolio.

Run with:

PYTHONPATH=src python3 -m open_portfolio.web_app

The module tries to import Flask and will show a helpful error if it's
not installed. The web UI is intentionally tiny: an overview page and a
form to submit a BUY/SELL transaction.
"""
from __future__ import annotations
import os
import sys
import signal
import subprocess
import time
from datetime import date

try:
    from flask import Flask, request, redirect, url_for, render_template
except Exception as e:  # pragma: no cover - runtime dependency
    Flask = None  # type: ignore

from .product_collection import ProductCollection
from .database import Database
from .transactions import TransactionManager
from .enums import TransactionTemplate, InstrumentType, PaymentFrequency
from .products import Product, Bond, Stock
from .order_entry import DatabaseOrderRepository, OrderStatus, placeholder_messages
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

def make_app(client=None, product_collection=None, currency_prices=None, order_database=None):

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
    tx_date_edit_enabled = os.getenv("OPEN_PORTFOLIO_ENABLE_TX_DATE_EDIT", "0").strip().lower() in {"1", "true", "yes", "on"}
    tx_manager = TransactionManager()
    if order_database is None:
        if os.getenv("PYTEST_CURRENT_TEST"):
            default_order_db_path = ":memory:"
        else:
            default_order_db_path = os.getenv("OPEN_PORTFOLIO_ORDER_DB_PATH", "open_portfolio_orders.sqlite3")
        order_database = Database(default_order_db_path)

    retention_raw = os.getenv("OPEN_PORTFOLIO_ORDER_DRAFT_RETENTION_DAYS", "30")
    try:
        retention_days = int(retention_raw)
    except ValueError:
        retention_days = 30
    startup_purged_drafts = order_database.purge_stale_order_drafts(retention_days=retention_days)

    order_repo = DatabaseOrderRepository(order_database)

    def restore_instruments_from_db():
        stored_instruments = order_database.list_instruments()
        for row in stored_instruments:
            instrument_type = (row.get("instrument_type") or "").upper()
            instrument_id = int(row["instrument_id"])
            description = row["description"]
            isin = row.get("isin") or ""
            issue_currency = (row.get("issue_currency") or "EUR").upper()
            minimum_purchase_value = float(row.get("minimum_purchase_value") or 1.0)
            smallest_trading_unit = float(row.get("smallest_trading_unit") or 1.0)

            if instrument_type == "BOND":
                start_date_raw = row.get("start_date")
                maturity_date_raw = row.get("maturity_date")
                if not start_date_raw or not maturity_date_raw:
                    continue
                try:
                    frequency = PaymentFrequency[(row.get("interest_payment_frequency") or "YEAR").upper()]
                except KeyError:
                    frequency = PaymentFrequency.YEAR
                product = Bond(
                    instrument_id=instrument_id,
                    description=description,
                    minimum_purchase_value=minimum_purchase_value,
                    smallest_trading_unit=smallest_trading_unit,
                    issue_currency=issue_currency,
                    start_date=date.fromisoformat(start_date_raw),
                    maturity_date=date.fromisoformat(maturity_date_raw),
                    interest_rate=float(row.get("interest_rate") or 0.0),
                    interest_payment_frequency=frequency,
                    isin=isin,
                )
            elif instrument_type == "STOCK":
                product = Stock(
                    product_id=instrument_id,
                    description=description,
                    minimum_purchase_value=minimum_purchase_value,
                    smallest_trading_unit=smallest_trading_unit,
                    issue_currency=issue_currency,
                    isin=isin,
                )
            elif instrument_type in {"OPTION", "FUND"}:
                product = Product(
                    instrument_id=instrument_id,
                    description=description,
                    product_type=InstrumentType[instrument_type],
                    minimum_purchase_value=minimum_purchase_value,
                    smallest_trading_unit=smallest_trading_unit,
                    issue_currency=issue_currency,
                    isin=isin,
                )
            else:
                continue
            product_collection.add_product(product)

    restore_instruments_from_db()

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

    def parse_float(value: str, field_name: str) -> float:
        text = (value or "").strip().replace(" ", "").replace(",", ".")
        if not text:
            raise ValueError(f"{field_name} is verplicht")
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} heeft geen geldig getal") from exc

    def parse_int(value: str, field_name: str) -> int:
        text = (value or "").strip()
        if not text:
            raise ValueError(f"{field_name} is verplicht")
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} heeft geen geldig geheel getal") from exc

    def parse_date_required(value: str, field_name: str) -> date:
        text = (value or "").strip()
        if not text:
            raise ValueError(f"{field_name} is verplicht")
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} heeft ongeldig formaat (YYYY-MM-DD)") from exc

    def format_coupon_percent(interest_rate_decimal) -> str:
        if interest_rate_decimal is None:
            return ""
        try:
            value = round(float(interest_rate_decimal) * 100.0, 6)
        except (TypeError, ValueError):
            return ""
        return f"{value:.6f}".rstrip("0").rstrip(".")

    def build_product_from_form(form_data, fixed_instrument_id=None):
        if fixed_instrument_id is None:
            instrument_id = parse_int(form_data.get("instrument_id", ""), "Instrument ID")
        else:
            instrument_id = fixed_instrument_id

        description = (form_data.get("description", "") or "").strip()
        if not description:
            raise ValueError("Omschrijving is verplicht")

        instrument_type_text = (form_data.get("instrument_type", "") or "").strip().upper()
        if instrument_type_text not in {"BOND", "STOCK", "OPTION", "FUND"}:
            raise ValueError("Instrumenttype is ongeldig")

        currency = (form_data.get("issue_currency", "") or "").strip().upper()
        if not currency:
            raise ValueError("Valuta is verplicht")

        isin = (form_data.get("isin", "") or "").strip().upper()
        min_purchase = parse_float(form_data.get("minimum_purchase_value", ""), "Minimale ordergrootte")
        trading_unit = parse_float(form_data.get("smallest_trading_unit", ""), "Handelseenheid")

        if instrument_type_text == "BOND":
            maturity_date_value = parse_date_required(form_data.get("maturity_date", ""), "Einddatum")
            coupon_percent = parse_float(form_data.get("interest_rate", ""), "Couponrente")
            interest_rate = coupon_percent / 100.0
            frequency_text = (form_data.get("interest_payment_frequency", "YEAR") or "YEAR").strip().upper()
            try:
                frequency = PaymentFrequency[frequency_text]
            except KeyError as exc:
                raise ValueError("Couponfrequentie is ongeldig") from exc

            return Bond(
                instrument_id=instrument_id,
                description=description,
                minimum_purchase_value=min_purchase,
                smallest_trading_unit=trading_unit,
                issue_currency=currency,
                start_date=date.today(),
                maturity_date=maturity_date_value,
                interest_rate=interest_rate,
                interest_payment_frequency=frequency,
                isin=isin,
            )

        if instrument_type_text == "STOCK":
            return Stock(
                product_id=instrument_id,
                description=description,
                minimum_purchase_value=min_purchase,
                smallest_trading_unit=trading_unit,
                issue_currency=currency,
                isin=isin,
            )

        return Product(
            instrument_id=instrument_id,
            description=description,
            product_type=InstrumentType[instrument_type_text],
            minimum_purchase_value=min_purchase,
            smallest_trading_unit=trading_unit,
            issue_currency=currency,
            isin=isin,
        )

    def instrument_to_payload(product):
        return {
            "instrument_id": product.instrument_id,
            "description": product.description,
            "instrument_type": product.type.name,
            "issue_currency": product.issue_currency,
            "minimum_purchase_value": product.minimum_purchase_value,
            "smallest_trading_unit": product.smallest_trading_unit,
            "start_date": getattr(product, "start_date", None).isoformat() if getattr(product, "start_date", None) else None,
            "maturity_date": getattr(product, "maturity_date", None).isoformat() if getattr(product, "maturity_date", None) else None,
            "interest_rate": getattr(product, "interest_rate", None),
            "interest_payment_frequency": getattr(getattr(product, "interest_payment_frequency", None), "name", None),
            "isin": getattr(product, "isin", ""),
        }

    def compact_number(value: float) -> str:
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.6f}".rstrip("0").rstrip(".")

    def format_position_for_product(product: Product, raw_amount: float) -> str:
        amount_text = compact_number(float(raw_amount))
        if product.is_bond():
            return f"{amount_text} {product.issue_currency}"
        return amount_text

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

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

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

        def get_latest_price_for_date(product, tx_date: date) -> tuple[float, date]:
            latest = None
            for p_date, p_value in product.prices:
                if p_date <= tx_date:
                    latest = (p_date, p_value)
                else:
                    break
            if latest is None:
                raise ValueError("Geen koers beschikbaar op of voor transactiedatum")
            return float(latest[1]), latest[0]

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
            locked_product_id_raw = request.form.get("locked_product_id", "")
            order_action = request.form.get("action", "")
            order_draft_id = request.form.get("order_draft_id", "")
            actor_id = request.form.get("actor_id", "")
            actor_role = request.form.get("actor_role", "")
            actor_channel = request.form.get("actor_channel", "web")
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
            locked_product_id_raw = request.args.get("locked_product_id", "")
            order_action = ""
            order_draft_id = request.args.get("order_draft_id", "")
            actor_id = request.args.get("actor_id", "")
            actor_role = request.args.get("actor_role", "")
            actor_channel = request.args.get("actor_channel", "web")

        if selected_product_id:
            try:
                selected_product_id = int(selected_product_id)
            except Exception:
                selected_product_id = None

        locked_product_id = None
        if locked_product_id_raw:
            try:
                locked_product_id = int(locked_product_id_raw)
            except Exception:
                locked_product_id = None

        instrument_locked = return_to == "holdings" and (locked_product_id is not None or selected_product_id is not None)
        if instrument_locked and locked_product_id is None:
            locked_product_id = selected_product_id
        if instrument_locked and locked_product_id is not None:
            selected_product_id = locked_product_id

        if request.method == "GET" and order_draft_id:
            existing_draft = order_repo.get_draft(order_draft_id)
            if existing_draft is not None:
                payload = existing_draft.payload or {}
                if request.args.get("template") is None:
                    selected_template = payload.get("template", selected_template)
                if request.args.get("order_type") is None:
                    selected_order_type = payload.get("order_type", selected_order_type)
                if request.args.get("product_id") is None:
                    selected_product_id = payload.get("product_id", selected_product_id)
                if request.args.get("settlement_currency") is None:
                    selected_settlement_currency = payload.get("settlement_currency", selected_settlement_currency)
                if request.args.get("amount") is None:
                    entered_amount = payload.get("amount", entered_amount)
                if request.args.get("price") is None:
                    entered_price = payload.get("price", entered_price)
                if request.args.get("transaction_date") is None:
                    entered_tx_date = payload.get("transaction_date", entered_tx_date)
                if request.args.get("actor_id") is None:
                    actor_id = payload.get("actor_id", actor_id)
                if request.args.get("actor_role") is None:
                    actor_role = payload.get("actor_role", actor_role)
                if request.args.get("actor_channel") is None:
                    actor_channel = payload.get("actor_channel", actor_channel)

        if selected_product_id:
            try:
                selected_product_id = int(selected_product_id)
            except Exception:
                selected_product_id = None

        active_products = sorted(
            product_collection.list_products(include_inactive=False, on_date=date.today()),
            key=lambda p: p.description.lower(),
        )
        active_product_ids = {product.instrument_id for product in active_products}

        selected_product = product_collection.search_product_id(selected_product_id) if selected_product_id else None
        selected_product_is_active = selected_product.instrument_id in active_product_ids if selected_product else False
        inactive_selected_product = selected_product if selected_product and not selected_product_is_active else None
        if selected_product_id is not None and not selected_product_is_active and not instrument_locked:
            selected_product_id = None
        product = selected_product if selected_product_is_active else None

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
        amount_unit_display = compact_number(float(amount_unit)) if amount_unit is not None else "-"
        minimum_order_size_display = compact_number(float(minimum_order_size)) if minimum_order_size is not None else "-"
        amount_suffix = product.issue_currency if is_bond and product else ""

        show_price_input = selected_order_type == "LIMIT"
        limit_suffix = "%" if is_bond and selected_order_type == "LIMIT" else (product.issue_currency if selected_order_type == "LIMIT" and product else "")

        estimated_trade = None
        estimated_cost = None
        estimated_accrued = None
        estimated_total = None
        used_price = None
        used_price_date = None
        order_status = "Nieuw"
        order_warnings = []
        order_placeholder_messages = placeholder_messages()

        def validate_and_calculate_order():
            if selected_portfolio is None:
                raise ValueError("Geen portefeuille geselecteerd")
            if inactive_selected_product is not None:
                raise ValueError("Instrument is inactief en kan niet verhandeld worden")
            if product is None:
                raise ValueError("Instrument niet gevonden")
            if selected_template not in {"BUY", "SELL"}:
                raise ValueError("Ongeldige transactiesoort")
            if selected_order_type not in {"MARKET", "LIMIT"}:
                raise ValueError("Ongeldig ordertype")

            tx_date_local = parse_tx_date(entered_tx_date)
            amount_local = parse_decimal(entered_amount, amount_label)
            if amount_local <= 0:
                raise ValueError(f"{amount_label} moet groter zijn dan 0")

            template_local = TransactionTemplate[selected_template]
            if template_local == TransactionTemplate.SELL and amount_local > current_position:
                raise ValueError("Onvoldoende positie voor verkoop")

            if amount_unit and not is_multiple_of_unit(amount_local, float(amount_unit)):
                raise ValueError(f"{amount_label} moet een veelvoud zijn van handelseenheid {amount_unit}")
            if template_local == TransactionTemplate.BUY and minimum_order_size and amount_local < float(minimum_order_size):
                raise ValueError(f"{amount_label} moet minimaal {minimum_order_size} zijn")

            if selected_order_type == "LIMIT":
                displayed_price_local = parse_decimal(entered_price, "Limiet")
                if displayed_price_local <= 0:
                    raise ValueError("Limiet moet groter zijn dan 0")
                displayed_price_date_local = None
            else:
                displayed_price_local, displayed_price_date_local = get_latest_price_for_date(product, tx_date_local)

            execution_price_local = to_execution_price(product, displayed_price_local)

            if selected_settlement_currency not in allowed_settlement_currencies:
                raise ValueError("Ongeldige afrekenrekening gekozen")
            if not selected_settlement_currency:
                raise ValueError("Geen afrekenrekening beschikbaar voor deze order")

            exchange_rate_local = get_fx(product.issue_currency, selected_settlement_currency)
            trade_amount_local = amount_local * execution_price_local * exchange_rate_local
            cost_local = calculate_cost(amount_local, execution_price_local) * exchange_rate_local
            accrued_local = 0.0
            if is_bond:
                accrued_local = product.calculate_accrued_interest(amount_local, tx_date_local) * exchange_rate_local

            if template_local == TransactionTemplate.SELL:
                total_local = trade_amount_local - cost_local + accrued_local
            else:
                total_local = trade_amount_local + cost_local + accrued_local

            if template_local == TransactionTemplate.BUY:
                estimated_cash_impact = trade_amount_local + cost_local + max(accrued_local, 0)
                if selected_settlement_balance is not None and estimated_cash_impact > float(selected_settlement_balance):
                    raise ValueError("Onvoldoende beschikbaar saldo op gekozen rekening")

            payload_local = {
                "transaction_date": tx_date_local,
                "portfolio_id": selected_portfolio.portfolio_id,
                "template": template_local,
                "portfolio": selected_portfolio,
                "product_collection": product_collection,
                "currency_prices": currency_prices,
                "product_id": product.instrument_id,
                "amount": amount_local,
                "price": execution_price_local,
                "transaction_currency": selected_settlement_currency,
                "exchange_rate": exchange_rate_local,
                "settlement_currency": selected_settlement_currency,
            }

            return {
                "payload": payload_local,
                "display_price": displayed_price_local,
                "display_price_date": displayed_price_date_local,
                "trade": trade_amount_local,
                "cost": cost_local,
                "accrued": accrued_local,
                "total": total_local,
            }

        if request.method == "POST" and (request.form.get("cancel") == "1" or order_action == "cancel"):
            if return_to == "holdings":
                return redirect(url_for("holdings_page", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
            return redirect(url_for("transactions", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))

        if request.method == "POST":
            effective_action = order_action
            if request.form.get("save") == "1" and not effective_action:
                effective_action = "submit"

            if effective_action in {"draft", "confirm", "submit"}:
                try:
                    result = validate_and_calculate_order()
                    used_price = result["display_price"]
                    used_price_date = result["display_price_date"]
                    estimated_trade = result["trade"]
                    estimated_cost = result["cost"]
                    estimated_accrued = result["accrued"]
                    estimated_total = result["total"]

                    entered_price = f"{used_price:.6f}".rstrip("0").rstrip(".")
                    payload_for_draft = {
                        "portfolio_id": selected_portfolio_id,
                        "client_id": selected_client_id,
                        "template": selected_template,
                        "order_type": selected_order_type,
                        "product_id": selected_product_id,
                        "settlement_currency": selected_settlement_currency,
                        "amount": entered_amount,
                        "price": entered_price,
                        "transaction_date": entered_tx_date,
                        "actor_id": actor_id,
                        "actor_role": actor_role,
                        "actor_channel": actor_channel,
                    }

                    if effective_action == "draft":
                        draft = order_repo.upsert_draft(
                            payload=payload_for_draft,
                            draft_id=order_draft_id or None,
                            status=OrderStatus.DRAFT,
                            warnings=order_placeholder_messages,
                        )
                        order_draft_id = draft.draft_id
                        order_status = "Concept"
                        success_message = f"Conceptorder opgeslagen ({draft.draft_id})"
                    elif effective_action == "confirm":
                        draft = order_repo.upsert_draft(
                            payload=payload_for_draft,
                            draft_id=order_draft_id or None,
                            status=OrderStatus.VALIDATED,
                            warnings=order_placeholder_messages,
                        )
                        order_draft_id = draft.draft_id
                        order_status = "Gevalideerd"
                        success_message = f"Order gevalideerd ({draft.draft_id}). Klik op Definitief boeken om uit te voeren."
                    else:
                        tx_manager.create_and_execute_transaction(**result["payload"])
                        if order_draft_id:
                            order_repo.set_status(order_draft_id, OrderStatus.SUBMITTED)
                        success_message = "Order definitief geboekt"
                        return redirect(url_for("transactions", client_id=selected_client.client_id, portfolio_id=selected_portfolio.portfolio_id))
                except Exception as exc:
                    if effective_action == "draft":
                        payload_for_draft = {
                            "portfolio_id": selected_portfolio_id,
                            "client_id": selected_client_id,
                            "template": selected_template,
                            "order_type": selected_order_type,
                            "product_id": selected_product_id,
                            "settlement_currency": selected_settlement_currency,
                            "amount": entered_amount,
                            "price": entered_price,
                            "transaction_date": entered_tx_date,
                            "actor_id": actor_id,
                            "actor_role": actor_role,
                            "actor_channel": actor_channel,
                        }
                        draft = order_repo.upsert_draft(
                            payload=payload_for_draft,
                            draft_id=order_draft_id or None,
                            status=OrderStatus.REJECTED,
                            errors=[str(exc)],
                            warnings=order_placeholder_messages,
                        )
                        order_draft_id = draft.draft_id
                        order_status = "Afgekeurd"
                    error = str(exc)

        if order_draft_id:
            existing_draft = order_repo.get_draft(order_draft_id)
            if existing_draft is not None:
                order_status = existing_draft.status.value.upper()
                order_warnings = list(existing_draft.warnings)

        if estimated_total is None:
            try:
                if product and selected_settlement_currency:
                    tx_date_preview = parse_tx_date(entered_tx_date)
                    amount_preview = parse_optional_decimal(entered_amount)
                    if selected_order_type == "MARKET":
                        used_price, used_price_date = get_latest_price_for_date(product, tx_date_preview)
                    else:
                        limit_preview = parse_optional_decimal(entered_price)
                        used_price = limit_preview if limit_preview is not None else None
                        used_price_date = None

                    if amount_preview and amount_preview > 0:
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

        instrument_choices = []
        for prod in active_products:
            pos = position_by_product.get(prod.instrument_id, 0.0)
            pos_text = format_position_for_product(prod, pos)
            isin_text = getattr(prod, "isin", "") or "-"
            label = f"[{product_kind(prod).upper()}] {prod.description} | ID: {prod.instrument_id} | ISIN: {isin_text} | Positie: {pos_text}"
            search_text = f"{prod.instrument_id} {prod.description} {isin_text}".lower()
            instrument_choices.append(
                {
                    "id": prod.instrument_id,
                    "label": label,
                    "search_text": search_text,
                }
            )

        selected_instrument_label = None
        if selected_product_id is not None:
            matched_choice = next((item for item in instrument_choices if item["id"] == selected_product_id), None)
            if matched_choice is not None:
                selected_instrument_label = matched_choice["label"]
            elif selected_product is not None:
                selected_instrument_label = f"[{product_kind(selected_product).upper()}] {selected_product.description} | ID: {selected_product.instrument_id}"

        return render_template(
            "transaction_form.html",
            clients=clients,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            templates=[TransactionTemplate.BUY, TransactionTemplate.SELL],
            products=product_collection.products,
            instrument_choices=instrument_choices,
            instrument_locked=instrument_locked,
            selected_instrument_label=selected_instrument_label,
            locked_product_id=locked_product_id,
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
            amount_unit_display=amount_unit_display,
            minimum_order_size=minimum_order_size,
            minimum_order_size_display=minimum_order_size_display,
            show_price_input=show_price_input,
            limit_suffix=limit_suffix,
            current_product_kind=current_product_kind,
            used_price=used_price,
            used_price_date=used_price_date,
            estimated_trade=estimated_trade,
            estimated_cost=estimated_cost,
            estimated_accrued=estimated_accrued,
            estimated_total=estimated_total,
            tx_date_edit_enabled=tx_date_edit_enabled,
            order_draft_id=order_draft_id,
            order_status=order_status,
            order_warnings=order_warnings,
            order_placeholder_messages=order_placeholder_messages,
            actor_id=actor_id,
            actor_role=actor_role,
            actor_channel=actor_channel,
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

    @app.route("/instruments", methods=["GET", "POST"])
    def instruments_page():
        if request.method == "POST":
            selected_client_id = request.form.get("client_id", type=int)
            selected_portfolio_id = request.form.get("portfolio_id", type=int)
        else:
            selected_client_id = request.args.get("client_id", type=int)
            selected_portfolio_id = request.args.get("portfolio_id", type=int)

        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        instrument_message = request.args.get("message")
        instrument_error = request.args.get("error")
        show_inactive = request.args.get("show_inactive", "0").strip().lower() in {"1", "true", "yes", "on"}

        if request.method == "POST":
            action = (request.form.get("action") or "").strip().lower()
            try:
                if action in {"add", "save"}:
                    fixed_id = None
                    if action == "save":
                        fixed_id = parse_int(request.form.get("instrument_id", ""), "Instrument ID")
                    product = build_product_from_form(request.form, fixed_instrument_id=fixed_id)
                    existing = product_collection.search_product_id(product.instrument_id)
                    if action == "add" and existing is not None:
                        raise ValueError("Instrument ID bestaat al")
                    product_collection.add_product(product)
                    order_database.upsert_instrument(instrument_to_payload(product))
                    if action == "add":
                        instrument_message = f"Instrument toegevoegd ({product.instrument_id})"
                    else:
                        instrument_message = f"Instrument opgeslagen ({product.instrument_id})"
                else:
                    instrument_error = "Onbekende actie op instrumentscherm"
            except ValueError as exc:
                instrument_error = str(exc)

        instruments = []
        filtered_products = sorted(
            product_collection.list_products(include_inactive=show_inactive, on_date=date.today()),
            key=lambda item: item.description.lower(),
        )
        for prod in filtered_products:
            pid = prod.instrument_id
            row = {
                "instrument_id": pid,
                "isin": getattr(prod, "isin", ""),
                "name": prod.description,
                "description": prod.description,
                "instrument_type": getattr(getattr(prod, "type", None), "name", "STOCK"),
                "issue_currency": prod.issue_currency,
                "is_active": prod.is_active(on_date=date.today()),
                "minimum_purchase_value": getattr(prod, "minimum_purchase_value", 0),
                "smallest_trading_unit": getattr(prod, "smallest_trading_unit", 0),
                "start_date": getattr(prod, "start_date", None),
                "maturity_date": getattr(prod, "maturity_date", None),
                "interest_rate": getattr(prod, "interest_rate", None),
                "interest_payment_frequency": getattr(getattr(prod, "interest_payment_frequency", None), "name", "YEAR"),
            }
            instruments.append(row)

        return render_template(
            "instruments.html",
            products=product_collection.products,
            instruments=instruments,
            instrument_types=["BOND", "STOCK"],
            payment_frequencies=[f.name for f in PaymentFrequency],
            show_inactive=show_inactive,
            instrument_message=instrument_message,
            instrument_error=instrument_error,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            active_page="instruments",
        )

    @app.route("/instruments/new", methods=["GET", "POST"])
    def new_instrument():
        selected_client_id = request.values.get("client_id", type=int)
        selected_portfolio_id = request.values.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)

        if request.method == "POST":
            try:
                product = build_product_from_form(request.form)
                if product_collection.search_product_id(product.instrument_id) is not None:
                    raise ValueError("Instrument ID bestaat al")
                product_collection.add_product(product)
                order_database.upsert_instrument(instrument_to_payload(product))
                return redirect(url_for("instruments_page", message=f"Instrument opgeslagen: {product.instrument_id}"))
            except ValueError as exc:
                return render_template(
                    "instrument_form.html",
                    instrument=dict(request.form),
                    instrument_types=["BOND", "STOCK"],
                    payment_frequencies=[f.name for f in PaymentFrequency],
                    action="add",
                    form_title="Nieuw instrument",
                    choose_type_mode=False,
                    instrument_error=str(exc),
                    selected_client=selected_client,
                    selected_portfolio=selected_portfolio,
                    selected_client_id=selected_client.client_id if selected_client else None,
                    selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
                    nav_query=nav_query(selected_client, selected_portfolio),
                    active_page="instruments",
                )

        instrument_type = (request.args.get("instrument_type") or "").strip().upper()
        if instrument_type not in {"BOND", "STOCK"}:
            return render_template(
                "instrument_form.html",
                instrument={"instrument_type": ""},
                instrument_types=["BOND", "STOCK"],
                payment_frequencies=[f.name for f in PaymentFrequency],
                action="add",
                form_title="Kies instrumenttype",
                choose_type_mode=True,
                selected_client=selected_client,
                selected_portfolio=selected_portfolio,
                selected_client_id=selected_client.client_id if selected_client else None,
                selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
                nav_query=nav_query(selected_client, selected_portfolio),
                active_page="instruments",
            )

        return render_template(
            "instrument_form.html",
            instrument={
                "instrument_type": instrument_type,
                "issue_currency": "EUR",
                "minimum_purchase_value": "1",
                "smallest_trading_unit": "1",
                "interest_payment_frequency": "YEAR",
            },
            instrument_types=["BOND", "STOCK"],
            payment_frequencies=[f.name for f in PaymentFrequency],
            action="add",
            form_title="Nieuw instrument",
            choose_type_mode=False,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            active_page="instruments",
        )

    @app.route("/instruments/edit/<int:instrument_id>", methods=["GET", "POST"])
    def edit_instrument(instrument_id):
        selected_client_id = request.values.get("client_id", type=int)
        selected_portfolio_id = request.values.get("portfolio_id", type=int)
        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)

        existing = product_collection.search_product_id(instrument_id)
        if existing is None:
            return "Instrument niet gevonden", 404

        if request.method == "POST":
            try:
                product = build_product_from_form(request.form, fixed_instrument_id=instrument_id)
                product_collection.add_product(product)
                order_database.upsert_instrument(instrument_to_payload(product))
                return redirect(url_for("instruments_page", message=f"Instrument opgeslagen: {instrument_id}"))
            except ValueError as exc:
                form_data = dict(request.form)
                form_data["instrument_id"] = str(instrument_id)
                return render_template(
                    "instrument_form.html",
                    instrument=form_data,
                    instrument_types=["BOND", "STOCK"],
                    payment_frequencies=[f.name for f in PaymentFrequency],
                    action="save",
                    form_title=f"Wijzig instrument {instrument_id}",
                    choose_type_mode=False,
                    instrument_error=str(exc),
                    selected_client=selected_client,
                    selected_portfolio=selected_portfolio,
                    selected_client_id=selected_client.client_id if selected_client else None,
                    selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
                    nav_query=nav_query(selected_client, selected_portfolio),
                    active_page="instruments",
                )

        instrument = {
            "instrument_id": existing.instrument_id,
            "isin": getattr(existing, "isin", ""),
            "description": existing.description,
            "instrument_type": existing.type.name,
            "issue_currency": existing.issue_currency,
            "minimum_purchase_value": existing.minimum_purchase_value,
            "smallest_trading_unit": existing.smallest_trading_unit,
            "maturity_date": getattr(existing, "maturity_date", None).isoformat() if getattr(existing, "maturity_date", None) else "",
            "interest_rate": format_coupon_percent(getattr(existing, "interest_rate", None)),
            "interest_payment_frequency": getattr(getattr(existing, "interest_payment_frequency", None), "name", "YEAR"),
        }

        return render_template(
            "instrument_form.html",
            instrument=instrument,
            instrument_types=["BOND", "STOCK"],
            payment_frequencies=[f.name for f in PaymentFrequency],
            action="save",
            form_title=f"Wijzig instrument {instrument_id}",
            choose_type_mode=False,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            active_page="instruments",
        )

    @app.route("/order-drafts", methods=["GET", "POST"])
    def order_drafts_page():
        if request.method == "POST":
            selected_client_id = request.form.get("client_id", type=int)
            selected_portfolio_id = request.form.get("portfolio_id", type=int)
        else:
            selected_client_id = request.args.get("client_id", type=int)
            selected_portfolio_id = request.args.get("portfolio_id", type=int)

        selected_client, selected_portfolio = resolve_context(selected_client_id, selected_portfolio_id)
        cleanup_message = None
        cleanup_error = None

        if request.method == "POST" and request.form.get("action") == "cleanup":
            confirm_cleanup = request.form.get("cleanup_confirm") == "1"
            retention_override = request.form.get("retention_days", "").strip()

            if not confirm_cleanup:
                cleanup_error = "Bevestiging vereist: vink opschonen aan om door te gaan."
            else:
                try:
                    cleanup_retention_days = retention_days
                    if retention_override:
                        cleanup_retention_days = int(retention_override)
                    if cleanup_retention_days <= 0:
                        raise ValueError("Retention moet groter zijn dan 0")
                    deleted = order_database.purge_stale_order_drafts(retention_days=cleanup_retention_days)
                    cleanup_message = f"Opschonen voltooid: {deleted} conceptorders verwijderd."
                except ValueError:
                    cleanup_error = "Retention heeft ongeldige waarde. Gebruik een geheel getal groter dan 0."

        drafts = order_database.list_order_drafts(limit=200)
        status_counts = order_database.get_order_draft_status_counts()

        return render_template(
            "order_drafts.html",
            drafts=drafts,
            status_counts=status_counts,
            startup_purged_drafts=startup_purged_drafts,
            retention_days=retention_days,
            cleanup_message=cleanup_message,
            cleanup_error=cleanup_error,
            selected_client=selected_client,
            selected_portfolio=selected_portfolio,
            selected_client_id=selected_client.client_id if selected_client else None,
            selected_portfolio_id=selected_portfolio.portfolio_id if selected_portfolio else None,
            nav_query=nav_query(selected_client, selected_portfolio),
            active_page="order-drafts",
        )

    return app



def run(host="127.0.0.1", port=5000):
    if Flask is None:
        print("Flask is not installed. Install with: pip install flask", file=sys.stderr)
        return

    # Sluit bestaande listeners op dezelfde poort voor een schone herstart.
    def pids_on_port(target_port: int):
        try:
            out = subprocess.check_output(["lsof", "-ti", f"tcp:{int(target_port)}"], text=True).strip()
        except Exception:
            return []
        return [int(pid) for pid in out.splitlines() if pid.strip()]

    for pid in pids_on_port(int(port)):
        if pid != os.getpid():
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

    time.sleep(0.35)

    for pid in pids_on_port(int(port)):
        if pid != os.getpid():
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    client, products_list, currency_prices = create_demo_data()
    # Rebuild ProductCollection from products list
    product_collection = ProductCollection()
    for prod in products_list:
        product_collection.add_product(prod)
    app = make_app(client, product_collection, currency_prices)
    app.run(host=host, port=port, use_reloader=False)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None, help="Poort voor de webserver")
    args = parser.parse_args()
    main_port = args.port or int(os.environ.get("OPEN_PORTFOLIO_PORT", 5000))
    run(port=main_port)
