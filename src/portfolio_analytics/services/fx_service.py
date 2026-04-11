"""
Mock FX service — deterministic exchange-rate provider.

All rates are expressed relative to EUR (the base currency).
Cross rates are derived via triangulation:
    USD/GBP = (USD/EUR) / (GBP/EUR)

Rates include a small daily wobble seeded by the date, so that the rate
on any given day is repeatable but not perfectly flat.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import date
from functools import lru_cache

from portfolio_analytics.domain.interfaces import FXServiceBase

# Base rates (1 unit of foreign currency = X EUR)
_BASE_RATES: dict[str, float] = {
    "EUR": 1.0,
    "USD": 0.91,   # 1 USD ≈ 0.91 EUR
    "GBP": 1.16,   # 1 GBP ≈ 1.16 EUR
    "CHF": 1.03,   # 1 CHF ≈ 1.03 EUR
    "JPY": 0.0061, # 1 JPY ≈ 0.0061 EUR
}

_WOBBLE_SIGMA = 0.002  # daily volatility around base rate


class MockFXService(FXServiceBase):
    """
    Deterministic FX rate service.

    Usage::

        fx = MockFXService()
        rate = fx.get_fx_rate("USD", "EUR", date(2025, 6, 15))
        eur_amount = usd_amount * rate
    """

    @lru_cache(maxsize=2048)
    def get_fx_rate(self, from_ccy: str, to_ccy: str, on_date: date) -> float:
        if from_ccy == to_ccy:
            return 1.0

        from_eur = self._rate_to_eur(from_ccy, on_date)
        to_eur = self._rate_to_eur(to_ccy, on_date)

        if to_eur == 0:
            raise ValueError(f"Zero rate for {to_ccy}")

        return from_eur / to_eur

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rate_to_eur(self, ccy: str, on_date: date) -> float:
        if ccy == "EUR":
            return 1.0
        base = _BASE_RATES.get(ccy)
        if base is None:
            raise ValueError(f"Unsupported currency: {ccy}")
        wobble = self._wobble(ccy, on_date)
        return base * (1.0 + wobble)

    @staticmethod
    def _wobble(ccy: str, on_date: date) -> float:
        key = f"{ccy}-{on_date.isoformat()}"
        seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        return rng.gauss(0, _WOBBLE_SIGMA)
