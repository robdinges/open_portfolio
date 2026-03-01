from __future__ import annotations
from datetime import date
from typing import List, Tuple
import logging

DEFAULT_CURRENCY = "EUR"


class CurrencyPrices:
    def __init__(self):
        self.prices: List[Tuple[str, date, float, str]] = []

    def add_price(self, currency_id: str, date_: date, price: float, counter_currency: str = DEFAULT_CURRENCY):
        new_price = (currency_id, date_, price, counter_currency)
        if new_price in self.prices:
            logging.warning("Price already exists: %s", new_price)
            return
        self.prices.append(new_price)
        logging.info("Added price %s", new_price)

    def get_latest_price(self, currency_id: str, counter_currency: str = DEFAULT_CURRENCY) -> float:
        relevant = [p for p in self.prices if p[0] == currency_id and p[3] == counter_currency]
        if relevant:
            return max(relevant, key=lambda r: r[1])[2]
        # try reverse
        rev = [p for p in self.prices if p[0] == counter_currency and p[3] == currency_id]
        if rev:
            return 1 / max(rev, key=lambda r: r[1])[2]
        raise ValueError(f"No exchange rate for {currency_id}/{counter_currency}")

    def show_prices(self, currency_id: str, start_date: date = date.today(), end_date: date = date(2099, 12, 31), counter_currency: str = DEFAULT_CURRENCY):
        return [p for p in self.prices if p[0] == currency_id and p[3] == counter_currency and start_date <= p[1] <= end_date]


class ProductPrices:
    def __init__(self, product_collection):
        self.product_collection = product_collection

    def add_price(self, product_id: int, date_: date, price: float, currency: str):
        prod = self.product_collection.search_product_id(product_id)
        if not prod:
            raise ValueError("Product not found")
        if prod.issue_currency != currency:
            raise ValueError("Currency mismatch")
        prod.add_price(date_, price)

    def show_prices(self, product_id: int, start_date: date = date.today(), end_date: date = date(2099, 12, 31)):
        prod = self.product_collection.search_product_id(product_id)
        if not prod:
            return []
        return [(d, p) for d, p in prod.prices if start_date <= d <= end_date]
