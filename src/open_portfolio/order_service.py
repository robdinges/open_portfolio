from __future__ import annotations

from datetime import date
from typing import Any

from .enums import TransactionTemplate


FEE_RATE = 0.001


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


def get_fx(currency_prices: Any, from_currency: str, to_currency: str) -> float:
    if from_currency == to_currency:
        return 1.0
    try:
        return float(currency_prices.get_latest_price(from_currency, to_currency))
    except Exception:
        try:
            return 1.0 / float(currency_prices.get_latest_price(to_currency, from_currency))
        except Exception as exc:
            raise ValueError(f"Geen wisselkoers beschikbaar voor {from_currency}/{to_currency}") from exc


def get_position_map(selected_portfolio: Any) -> dict[int, float]:
    result: dict[int, float] = {}
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


def build_settlement_options(selected_portfolio: Any, product: Any) -> tuple[list[dict], bool]:
    options: list[dict] = []
    locked = False
    default_currency = getattr(selected_portfolio, "default_currency", "EUR") if selected_portfolio else "EUR"
    if not selected_portfolio or not product:
        return options, locked

    cash_by_currency: dict[str, Any] = {}
    for account in selected_portfolio.cash_accounts.values():
        if getattr(getattr(account, "account_type", None), "name", "") != "CASH":
            continue
        curr = getattr(account, "currency", None)
        if curr and curr not in cash_by_currency:
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

    if not options:
        for curr, account in cash_by_currency.items():
            options.append({"currency": curr, "balance": account.balance})
    return options, locked


def is_multiple_of_unit(value: float, unit: float) -> bool:
    if unit <= 0:
        return True
    quotient = value / unit
    return abs(round(quotient) - quotient) <= 1e-9


def get_latest_price_for_date(product: Any, tx_date: date) -> tuple[float, date]:
    latest = None
    for p_date, p_value in product.prices:
        if p_date <= tx_date:
            latest = (p_date, p_value)
        else:
            break
    if latest is None:
        raise ValueError("Geen koers beschikbaar op of voor transactiedatum")
    return float(latest[1]), latest[0]


def calculate_cost(amount: float, execution_price: float, fx_rate: float = 1.0) -> float:
    return FEE_RATE * amount * execution_price * fx_rate


def product_kind(product: Any) -> str:
    kind = getattr(getattr(product, "type", None), "name", "")
    return kind.lower() if kind else "unknown"


def to_execution_price(product: Any, displayed_price: float) -> float:
    if product_kind(product) == "bond":
        return displayed_price / 100.0
    return displayed_price


def validate_and_calculate_order(
    *,
    portfolio: Any,
    product: Any,
    inactive_product: Any | None,
    template: str,
    order_type: str,
    entered_amount: str,
    entered_price: str,
    entered_tx_date: str,
    settlement_currency: str,
    settlement_balance: float | None,
    allowed_settlement_currencies: list[str],
    current_position: float,
    amount_label: str,
    amount_unit: float | None,
    minimum_order_size: float | None,
    is_bond: bool,
    currency_prices: Any,
    product_collection: Any,
) -> dict:
    if portfolio is None:
        raise ValueError("Geen portefeuille geselecteerd")
    if inactive_product is not None:
        raise ValueError("Instrument is inactief en kan niet verhandeld worden")
    if product is None:
        raise ValueError("Instrument niet gevonden")
    if template not in {"BUY", "SELL"}:
        raise ValueError("Ongeldige transactiesoort")
    if order_type not in {"MARKET", "LIMIT"}:
        raise ValueError("Ongeldig ordertype")

    tx_date_local = parse_tx_date(entered_tx_date)
    amount_local = parse_decimal(entered_amount, amount_label)
    if amount_local <= 0:
        raise ValueError(f"{amount_label} moet groter zijn dan 0")

    template_local = TransactionTemplate[template]
    if template_local == TransactionTemplate.SELL and amount_local > current_position:
        raise ValueError("Onvoldoende positie voor verkoop")

    if amount_unit and not is_multiple_of_unit(amount_local, float(amount_unit)):
        raise ValueError(f"{amount_label} moet een veelvoud zijn van handelseenheid {amount_unit}")
    if minimum_order_size and amount_local < float(minimum_order_size):
        raise ValueError(f"{amount_label} moet minimaal {minimum_order_size} zijn")

    if order_type == "LIMIT":
        displayed_price_local = parse_decimal(entered_price, "Limiet")
        if displayed_price_local <= 0:
            raise ValueError("Limiet moet groter zijn dan 0")
        displayed_price_date_local = None
    else:
        displayed_price_local, displayed_price_date_local = get_latest_price_for_date(product, tx_date_local)

    execution_price_local = to_execution_price(product, displayed_price_local)

    if settlement_currency not in allowed_settlement_currencies:
        raise ValueError("Ongeldige afrekenrekening gekozen")
    if not settlement_currency:
        raise ValueError("Geen afrekenrekening beschikbaar voor deze order")

    exchange_rate_local = get_fx(currency_prices, product.issue_currency, settlement_currency)
    trade_amount_local = amount_local * execution_price_local * exchange_rate_local
    cost_local = calculate_cost(amount_local, execution_price_local, exchange_rate_local)
    accrued_abs = 0.0
    if is_bond:
        accrued_abs = product.calculate_accrued_interest(amount_local, tx_date_local) * exchange_rate_local

    if template_local == TransactionTemplate.SELL:
        accrued_display = abs(accrued_abs)
        total_local = trade_amount_local - cost_local + accrued_abs
    else:
        accrued_display = -abs(accrued_abs) if accrued_abs != 0.0 else 0.0
        total_local = trade_amount_local + cost_local + accrued_abs

    if template_local == TransactionTemplate.BUY:
        estimated_cash_impact = trade_amount_local + cost_local + max(accrued_abs, 0)
        if settlement_balance is not None and estimated_cash_impact > float(settlement_balance):
            raise ValueError("Onvoldoende beschikbaar saldo op gekozen rekening")

    payload_local = {
        "transaction_date": tx_date_local,
        "portfolio_id": portfolio.portfolio_id,
        "template": template_local,
        "portfolio": portfolio,
        "product_collection": product_collection,
        "currency_prices": currency_prices,
        "product_id": product.instrument_id,
        "amount": amount_local,
        "price": execution_price_local,
        "transaction_currency": settlement_currency,
        "exchange_rate": exchange_rate_local,
        "settlement_currency": settlement_currency,
    }

    return {
        "payload": payload_local,
        "display_price": displayed_price_local,
        "display_price_date": displayed_price_date_local,
        "trade": trade_amount_local,
        "cost": cost_local,
        "accrued": accrued_display,
        "total": total_local,
    }
