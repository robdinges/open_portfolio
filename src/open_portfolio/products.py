from __future__ import annotations
from datetime import date, timedelta
import calendar
from typing import List, Tuple, Dict
import logging

from .enums import InstrumentType, PaymentFrequency, InterestType


class Product:
    def __init__(
        self,
        instrument_id: int,
        description: str,
        product_type: InstrumentType,
        minimum_purchase_value: float,
        smallest_trading_unit: float,
        issue_currency: str,
        isin: str = ""
    ):
        self.instrument_id = instrument_id
        self.description = description
        self.type = product_type
        self.minimum_purchase_value = minimum_purchase_value
        self.smallest_trading_unit = smallest_trading_unit
        self.issue_currency = issue_currency
        self.isin = isin
        self.prices: List[Tuple[date, float]] = []
        self.transactions: List = []  # filled by TransactionManager

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
        logging.debug("Added transaction to product %s", self.instrument_id)

    def add_price(self, date_: date, price: float):
        self.prices.append((date_, price))
        self.prices.sort()
        logging.debug("Added price for %s on %s", self.instrument_id, date_)

    def get_price(self, date_: date) -> float | None:
        last = None
        for d, p in self.prices:
            if d <= date_:
                last = p
            else:
                break
        return last

    def is_bond(self) -> bool:
        return self.type == InstrumentType.BOND

    def is_active(self, on_date: date | None = None) -> bool:
        del on_date
        return True

    def to_dict(self) -> Dict:
        return {
            "instrument_id": self.instrument_id,
            "description": self.description,
            "type": self.type.name,
            "currency": self.issue_currency,
            "isin": self.isin,
        }


class Bond(Product):
    def __init__(
        self,
        instrument_id: int,
        description: str,
        minimum_purchase_value: float,
        smallest_trading_unit: float,
        issue_currency: str,
        start_date: date,
        maturity_date: date,
        interest_rate: float,
        interest_payment_frequency: PaymentFrequency,
        isin: str = ""
    ):
        super().__init__(
            instrument_id,
            description,
            InstrumentType.BOND,
            minimum_purchase_value,
            smallest_trading_unit,
            issue_currency,
            isin=isin
        )
        self.start_date = start_date
        self.maturity_date = maturity_date
        self.interest_rate = interest_rate
        self.interest_payment_frequency = interest_payment_frequency

    def calculate_accrued_interest(
        self,
        nominal_value: float,
        valuation_date: date,
        interest_type: InterestType = InterestType.ACT_ACT,
    ) -> float:
        if interest_type == InterestType.ACT_ACT:
            return self._calculate_act_act(nominal_value, valuation_date)
        else:
            return self._calculate_thirty_360(nominal_value, valuation_date)

    def _previous_coupon_date(self, valuation_date: date) -> date:
        # Keep legacy behavior for valuation dates before start date.
        if valuation_date < self.start_date:
            return self.start_date

        if self.interest_payment_frequency == PaymentFrequency.END_DATE:
            # Zero-coupon style behavior: accrue from start date up to maturity.
            return self.start_date

        if self.interest_payment_frequency == PaymentFrequency.MONTH:
            coupon_date = self.start_date
            while True:
                next_coupon = self._add_months(coupon_date, 1)
                if next_coupon > valuation_date:
                    return coupon_date
                coupon_date = next_coupon

        # Default annual coupon cycle.
        coupon_date = self.start_date
        while True:
            next_coupon = self._add_years(coupon_date, 1)
            if next_coupon > valuation_date:
                return coupon_date
            coupon_date = next_coupon

    def _add_months(self, d: date, months: int) -> date:
        month_index = (d.month - 1) + months
        year = d.year + month_index // 12
        month = (month_index % 12) + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _add_years(self, d: date, years: int) -> date:
        year = d.year + years
        day = min(d.day, calendar.monthrange(year, d.month)[1])
        return date(year, d.month, day)

    def _calculate_act_act(self, nominal_value: float, valuation_date: date) -> float:
        period_start = self._previous_coupon_date(valuation_date)
        days = (valuation_date - period_start).days
        yearlen = 366 if self._contains_leap_year(period_start, valuation_date) else 365
        return nominal_value * self.interest_rate * days / yearlen

    def _calculate_thirty_360(self, nominal_value: float, valuation_date: date) -> float:
        period_start = self._previous_coupon_date(valuation_date)
        days = (
            (valuation_date.year - period_start.year) * 360
            + (valuation_date.month - period_start.month) * 30
            + (valuation_date.day - period_start.day)
        )
        return nominal_value * self.interest_rate * days / 360

    def _contains_leap_year(self, a: date, b: date) -> bool:
        d = a
        while d <= b:
            if d.month == 2 and d.day == 29:
                return True
            d += timedelta(days=1)
        return False

    def is_active(self, on_date: date | None = None) -> bool:
        ref_date = on_date or date.today()
        return self.maturity_date >= ref_date


class Stock(Product):
    def __init__(
        self,
        product_id: int,
        description: str,
        minimum_purchase_value: float,
        smallest_trading_unit: float,
        issue_currency: str,
        isin: str = ""
    ):
        super().__init__(
            product_id,
            description,
            InstrumentType.STOCK,
            minimum_purchase_value,
            smallest_trading_unit,
            issue_currency,
            isin=isin
        )
