from __future__ import annotations

import pytest
from datetime import date
from unittest.mock import MagicMock

from open_portfolio.order_service import (
    parse_decimal,
    parse_optional_decimal,
    parse_tx_date,
    get_fx,
    get_position_map,
    build_settlement_options,
    is_multiple_of_unit,
    get_latest_price_for_date,
    calculate_cost,
    product_kind,
    to_execution_price,
    validate_and_calculate_order,
    FEE_RATE,
)
from open_portfolio.enums import InstrumentType, TransactionTemplate


# --- Helpers to build mock objects ---

def make_product(instrument_id=1, description="Test Stock", ptype=InstrumentType.STOCK,
                 issue_currency="EUR", prices=None, minimum_purchase_value=0,
                 smallest_trading_unit=1):
    p = MagicMock()
    p.instrument_id = instrument_id
    p.description = description
    p.type = ptype
    p.issue_currency = issue_currency
    p.prices = prices or []
    p.minimum_purchase_value = minimum_purchase_value
    p.smallest_trading_unit = smallest_trading_unit
    p.is_bond = MagicMock(return_value=(ptype == InstrumentType.BOND))
    p.calculate_accrued_interest = MagicMock(return_value=0.0)
    return p


def make_portfolio(portfolio_id=1, default_currency="EUR", cash_accounts=None,
                   securities_account=None):
    p = MagicMock()
    p.portfolio_id = portfolio_id
    p.default_currency = default_currency
    p.cash_accounts = cash_accounts or {}
    p.securities_account = securities_account
    return p


def make_cash_account(currency="EUR", balance=100000.0):
    a = MagicMock()
    a.currency = currency
    a.balance = balance
    a.account_type = MagicMock()
    a.account_type.name = "CASH"
    return a


def make_currency_prices(rates=None):
    cp = MagicMock()
    _rates = rates or {}
    def get_latest_price(from_c, to_c):
        key = f"{from_c}/{to_c}"
        if key in _rates:
            return _rates[key]
        raise ValueError(f"No rate for {key}")
    cp.get_latest_price = MagicMock(side_effect=get_latest_price)
    return cp


# --- parse_decimal ---

class TestParseDecimal:
    def test_valid_comma(self):
        assert parse_decimal("100,50", "Bedrag") == 100.50

    def test_valid_dot(self):
        assert parse_decimal("100.50", "Bedrag") == 100.50

    def test_strips_spaces(self):
        assert parse_decimal(" 1 000,50 ", "Bedrag") == 1000.50

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="verplicht"):
            parse_decimal("", "Bedrag")

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="geldig getal"):
            parse_decimal("abc", "Bedrag")


# --- parse_optional_decimal ---

class TestParseOptionalDecimal:
    def test_valid(self):
        assert parse_optional_decimal("42,5") == 42.5

    def test_empty_returns_none(self):
        assert parse_optional_decimal("") is None

    def test_whitespace_returns_none(self):
        assert parse_optional_decimal("  ") is None


# --- parse_tx_date ---

class TestParseTxDate:
    def test_valid_iso(self):
        assert parse_tx_date("2026-03-15") == date(2026, 3, 15)

    def test_empty_returns_today(self):
        assert parse_tx_date("") == date.today()

    def test_none_returns_today(self):
        assert parse_tx_date(None) == date.today()

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="ongeldig formaat"):
            parse_tx_date("15-03-2026-extra")

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="ongeldig"):
            parse_tx_date("2026-02-30")


# --- get_fx ---

class TestGetFx:
    def test_same_currency(self):
        cp = make_currency_prices()
        assert get_fx(cp, "EUR", "EUR") == 1.0

    def test_direct_rate(self):
        cp = make_currency_prices({"EUR/USD": 1.10})
        assert get_fx(cp, "EUR", "USD") == 1.10

    def test_reverse_rate(self):
        cp = make_currency_prices({"USD/EUR": 0.90})
        result = get_fx(cp, "EUR", "USD")
        assert abs(result - 1.0 / 0.90) < 1e-9

    def test_no_rate_raises(self):
        cp = make_currency_prices()
        with pytest.raises(ValueError, match="wisselkoers"):
            get_fx(cp, "EUR", "GBP")


# --- is_multiple_of_unit ---

class TestIsMultipleOfUnit:
    def test_exact_multiple(self):
        assert is_multiple_of_unit(100.0, 10.0) is True

    def test_not_multiple(self):
        assert is_multiple_of_unit(15.0, 10.0) is False

    def test_zero_unit(self):
        assert is_multiple_of_unit(15.0, 0.0) is True

    def test_small_unit(self):
        assert is_multiple_of_unit(0.03, 0.01) is True


# --- get_latest_price_for_date ---

class TestGetLatestPriceForDate:
    def test_exact_date(self):
        product = make_product(prices=[(date(2026, 3, 1), 100.0), (date(2026, 3, 15), 105.0)])
        price, pdate = get_latest_price_for_date(product, date(2026, 3, 15))
        assert price == 105.0
        assert pdate == date(2026, 3, 15)

    def test_earlier_date(self):
        product = make_product(prices=[(date(2026, 3, 1), 100.0), (date(2026, 3, 15), 105.0)])
        price, pdate = get_latest_price_for_date(product, date(2026, 3, 10))
        assert price == 100.0
        assert pdate == date(2026, 3, 1)

    def test_no_price_raises(self):
        product = make_product(prices=[(date(2026, 3, 15), 105.0)])
        with pytest.raises(ValueError, match="Geen koers"):
            get_latest_price_for_date(product, date(2026, 3, 1))


# --- calculate_cost ---

class TestCalculateCost:
    def test_basic(self):
        cost = calculate_cost(100, 50.0)
        assert abs(cost - FEE_RATE * 100 * 50.0) < 1e-9

    def test_with_fx(self):
        cost = calculate_cost(100, 50.0, 1.10)
        assert abs(cost - FEE_RATE * 100 * 50.0 * 1.10) < 1e-9


# --- product_kind ---

class TestProductKind:
    def test_bond(self):
        p = make_product(ptype=InstrumentType.BOND)
        assert product_kind(p) == "bond"

    def test_stock(self):
        p = make_product(ptype=InstrumentType.STOCK)
        assert product_kind(p) == "stock"

    def test_none_product(self):
        assert product_kind(None) == "unknown"


# --- to_execution_price ---

class TestToExecutionPrice:
    def test_bond_divides_by_100(self):
        p = make_product(ptype=InstrumentType.BOND)
        assert to_execution_price(p, 101.5) == pytest.approx(1.015)

    def test_stock_passthrough(self):
        p = make_product(ptype=InstrumentType.STOCK)
        assert to_execution_price(p, 50.0) == 50.0


# --- build_settlement_options ---

class TestBuildSettlementOptions:
    def test_same_currency_locked(self):
        eur_account = make_cash_account("EUR", 50000.0)
        portfolio = make_portfolio(
            default_currency="EUR",
            cash_accounts={("1", "EUR", "CASH"): eur_account},
        )
        product = make_product(issue_currency="EUR")
        options, locked = build_settlement_options(portfolio, product)
        assert locked is True
        assert len(options) == 1
        assert options[0]["currency"] == "EUR"

    def test_different_currency_unlocked(self):
        eur_account = make_cash_account("EUR", 50000.0)
        usd_account = make_cash_account("USD", 30000.0)
        portfolio = make_portfolio(
            default_currency="EUR",
            cash_accounts={
                ("1", "EUR", "CASH"): eur_account,
                ("2", "USD", "CASH"): usd_account,
            },
        )
        product = make_product(issue_currency="USD")
        options, locked = build_settlement_options(portfolio, product)
        assert locked is False
        assert len(options) == 2
        currencies = {opt["currency"] for opt in options}
        assert currencies == {"EUR", "USD"}

    def test_no_product_empty(self):
        portfolio = make_portfolio()
        options, locked = build_settlement_options(portfolio, None)
        assert options == []
        assert locked is False


# --- validate_and_calculate_order ---

def _base_order_kwargs(product=None, portfolio=None, currency_prices=None):
    if product is None:
        product = make_product(
            prices=[(date(2026, 3, 1), 50.0)],
            issue_currency="EUR",
            smallest_trading_unit=1,
            minimum_purchase_value=0,
        )
    if portfolio is None:
        portfolio = make_portfolio()
    if currency_prices is None:
        currency_prices = make_currency_prices()
    return {
        "portfolio": portfolio,
        "product": product,
        "inactive_product": None,
        "template": "BUY",
        "order_type": "MARKET",
        "entered_amount": "10",
        "entered_price": "",
        "entered_tx_date": "2026-03-01",
        "settlement_currency": "EUR",
        "settlement_balance": 100000.0,
        "allowed_settlement_currencies": ["EUR"],
        "current_position": 0.0,
        "amount_label": "Aantal",
        "amount_unit": 1,
        "minimum_order_size": 0,
        "is_bond": False,
        "currency_prices": currency_prices,
        "product_collection": MagicMock(),
    }


class TestValidateAndCalculateOrder:
    def test_basic_buy_stock(self):
        result = validate_and_calculate_order(**_base_order_kwargs())
        assert result["trade"] == pytest.approx(-(10 * 50.0))
        assert result["cost"] == pytest.approx(-(FEE_RATE * 10 * 50.0))
        assert result["accrued"] == 0.0
        assert result["total"] == pytest.approx(-(10 * 50.0 + FEE_RATE * 10 * 50.0))

    def test_no_portfolio_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["portfolio"] = None
        with pytest.raises(ValueError, match="portefeuille"):
            validate_and_calculate_order(**kwargs)

    def test_no_product_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["product"] = None
        with pytest.raises(ValueError, match="niet gevonden"):
            validate_and_calculate_order(**kwargs)

    def test_inactive_product_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["inactive_product"] = MagicMock()
        with pytest.raises(ValueError, match="inactief"):
            validate_and_calculate_order(**kwargs)

    def test_invalid_template_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["template"] = "DEPOSIT"
        with pytest.raises(ValueError, match="transactiesoort"):
            validate_and_calculate_order(**kwargs)

    def test_invalid_order_type_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["order_type"] = "STOP"
        with pytest.raises(ValueError, match="ordertype"):
            validate_and_calculate_order(**kwargs)

    def test_zero_amount_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["entered_amount"] = "0"
        with pytest.raises(ValueError, match="groter zijn dan 0"):
            validate_and_calculate_order(**kwargs)

    def test_sell_exceeds_position_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["template"] = "SELL"
        kwargs["entered_amount"] = "100"
        kwargs["current_position"] = 50.0
        with pytest.raises(ValueError, match="Onvoldoende positie"):
            validate_and_calculate_order(**kwargs)

    def test_sell_within_position(self):
        kwargs = _base_order_kwargs()
        kwargs["template"] = "SELL"
        kwargs["entered_amount"] = "5"
        kwargs["current_position"] = 50.0
        result = validate_and_calculate_order(**kwargs)
        assert result["trade"] == pytest.approx(5 * 50.0)
        expected_cost = FEE_RATE * 5 * 50.0
        assert result["cost"] == pytest.approx(-expected_cost)
        assert result["total"] == pytest.approx(5 * 50.0 - expected_cost)

    def test_not_multiple_of_unit_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["entered_amount"] = "15"
        kwargs["amount_unit"] = 10
        with pytest.raises(ValueError, match="veelvoud"):
            validate_and_calculate_order(**kwargs)

    def test_below_minimum_order_buy_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["entered_amount"] = "5"
        kwargs["minimum_order_size"] = 10
        with pytest.raises(ValueError, match="minimaal"):
            validate_and_calculate_order(**kwargs)

    def test_below_minimum_order_sell_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["template"] = "SELL"
        kwargs["entered_amount"] = "5"
        kwargs["current_position"] = 50.0
        kwargs["minimum_order_size"] = 10
        with pytest.raises(ValueError, match="minimaal"):
            validate_and_calculate_order(**kwargs)

    def test_limit_order(self):
        kwargs = _base_order_kwargs()
        kwargs["order_type"] = "LIMIT"
        kwargs["entered_price"] = "55"
        result = validate_and_calculate_order(**kwargs)
        assert result["display_price"] == 55.0
        assert result["display_price_date"] is None
        assert result["trade"] == pytest.approx(-(10 * 55.0))

    def test_limit_zero_price_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["order_type"] = "LIMIT"
        kwargs["entered_price"] = "0"
        with pytest.raises(ValueError, match="groter zijn dan 0"):
            validate_and_calculate_order(**kwargs)

    def test_invalid_settlement_currency_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["settlement_currency"] = "GBP"
        with pytest.raises(ValueError, match="Ongeldige afrekenrekening"):
            validate_and_calculate_order(**kwargs)

    def test_insufficient_balance_raises(self):
        kwargs = _base_order_kwargs()
        kwargs["settlement_balance"] = 1.0
        with pytest.raises(ValueError, match="Onvoldoende beschikbaar saldo"):
            validate_and_calculate_order(**kwargs)

    def test_bond_accrued_interest_buy(self):
        product = make_product(
            ptype=InstrumentType.BOND,
            issue_currency="EUR",
            prices=[(date(2026, 3, 1), 101.0)],
            smallest_trading_unit=1000,
            minimum_purchase_value=0,
        )
        product.calculate_accrued_interest = MagicMock(return_value=250.0)
        kwargs = _base_order_kwargs(product=product)
        kwargs["entered_amount"] = "10000"
        kwargs["is_bond"] = True
        kwargs["amount_label"] = "Nominale waarde"
        kwargs["amount_unit"] = 1000
        result = validate_and_calculate_order(**kwargs)
        exec_price = 101.0 / 100.0
        expected_trade = 10000 * exec_price
        expected_cost = FEE_RATE * 10000 * exec_price
        assert result["trade"] == pytest.approx(-expected_trade)
        assert result["cost"] == pytest.approx(-expected_cost)
        assert result["accrued"] == pytest.approx(-250.0)
        assert result["total"] == pytest.approx(-(expected_trade + expected_cost + 250.0))

    def test_bond_accrued_interest_sell(self):
        product = make_product(
            ptype=InstrumentType.BOND,
            issue_currency="EUR",
            prices=[(date(2026, 3, 1), 101.0)],
            smallest_trading_unit=1000,
            minimum_purchase_value=0,
        )
        product.calculate_accrued_interest = MagicMock(return_value=250.0)
        kwargs = _base_order_kwargs(product=product)
        kwargs["template"] = "SELL"
        kwargs["entered_amount"] = "10000"
        kwargs["current_position"] = 50000.0
        kwargs["is_bond"] = True
        kwargs["amount_label"] = "Nominale waarde"
        kwargs["amount_unit"] = 1000
        result = validate_and_calculate_order(**kwargs)
        exec_price = 101.0 / 100.0
        expected_trade = 10000 * exec_price
        expected_cost = FEE_RATE * 10000 * exec_price
        assert result["trade"] == pytest.approx(expected_trade)
        assert result["cost"] == pytest.approx(-expected_cost)
        assert result["accrued"] == pytest.approx(250.0)
        assert result["total"] == pytest.approx(expected_trade - expected_cost + 250.0)

    def test_payload_contains_required_keys(self):
        result = validate_and_calculate_order(**_base_order_kwargs())
        payload = result["payload"]
        assert "transaction_date" in payload
        assert "portfolio_id" in payload
        assert "template" in payload
        assert "product_id" in payload
        assert "amount" in payload
        assert "price" in payload
        assert "settlement_currency" in payload
        assert "exchange_rate" in payload
