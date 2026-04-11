"""
Mock pricing service — deterministic, seeded price generation.

Stock prices follow a **Geometric Brownian Motion** (GBM):
    S(t+1) = S(t) · exp((μ − σ²/2)·Δt + σ·√Δt · Z)

Bond prices follow a **mean-reverting Ornstein–Uhlenbeck** process:
    P(t+1) = P(t) + θ·(μ − P(t))·Δt + σ·√Δt · Z

Determinism is guaranteed by deriving a per-instrument PRNG seed from the
instrument ID, so the same ID always produces the same price path.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

from portfolio_analytics.domain.enums import InstrumentType
from portfolio_analytics.domain.interfaces import PricingServiceBase
from portfolio_analytics.domain.models import Instrument
from portfolio_analytics.repositories.base import InstrumentRepository
from portfolio_analytics.utils.date_utils import date_range

# GBM parameters (stocks)
_STOCK_MU = 0.08        # 8 % annualised drift
_STOCK_SIGMA = 0.20     # 20 % annualised volatility
_STOCK_S0_MIN = 20.0
_STOCK_S0_MAX = 500.0

# OU parameters (bonds)
_BOND_THETA = 0.5       # mean-reversion speed
_BOND_MU = 100.0        # long-run mean (par)
_BOND_SIGMA = 2.0       # low volatility
_BOND_P0_MIN = 95.0
_BOND_P0_MAX = 105.0

_DT = 1.0 / 252         # one trading day


class MockPricingService(PricingServiceBase):
    """
    Deterministic mock pricing backed by seeded random number generators.

    Results are cached per ``(instrument_id, date)`` to avoid redundant
    recomputation on repeated analytics queries.
    """

    def __init__(
        self,
        instrument_repo: InstrumentRepository,
        base_date: date = date(2024, 1, 1),
    ) -> None:
        self._instrument_repo = instrument_repo
        self._base_date = base_date

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_price(self, instrument_id: str, on_date: date) -> float:
        series = self._build_series(instrument_id, on_date)
        return series[-1][1]

    def get_price_series(
        self, instrument_id: str, start: date, end: date
    ) -> list[tuple[date, float]]:
        full = self._build_series(instrument_id, end)
        return [(d, p) for d, p in full if start <= d <= end]

    # ------------------------------------------------------------------
    # Internal — series generation with caching
    # ------------------------------------------------------------------

    @lru_cache(maxsize=512)
    def _build_series(
        self, instrument_id: str, up_to: date
    ) -> tuple[tuple[date, float], ...]:
        instrument = self._instrument_repo.get(instrument_id)
        if instrument is None:
            raise ValueError(f"Unknown instrument: {instrument_id}")

        rng = self._rng_for(instrument_id)

        if instrument.type == InstrumentType.BOND:
            s0 = _BOND_P0_MIN + rng.random() * (_BOND_P0_MAX - _BOND_P0_MIN)
            return tuple(self._ou_path(rng, s0, up_to))
        else:
            s0 = _STOCK_S0_MIN + rng.random() * (_STOCK_S0_MAX - _STOCK_S0_MIN)
            return tuple(self._gbm_path(rng, s0, up_to))

    def _gbm_path(
        self, rng: random.Random, s0: float, up_to: date
    ) -> list[tuple[date, float]]:
        days = date_range(self._base_date, up_to)
        prices: list[tuple[date, float]] = []
        s = s0
        for d in days:
            if d.weekday() >= 5:
                continue
            z = rng.gauss(0, 1)
            s *= math.exp(
                (_STOCK_MU - 0.5 * _STOCK_SIGMA**2) * _DT
                + _STOCK_SIGMA * math.sqrt(_DT) * z
            )
            prices.append((d, round(s, 4)))
        return prices

    def _ou_path(
        self, rng: random.Random, p0: float, up_to: date
    ) -> list[tuple[date, float]]:
        days = date_range(self._base_date, up_to)
        prices: list[tuple[date, float]] = []
        p = p0
        for d in days:
            if d.weekday() >= 5:
                continue
            z = rng.gauss(0, 1)
            p += _BOND_THETA * (_BOND_MU - p) * _DT + _BOND_SIGMA * math.sqrt(_DT) * z
            p = max(p, 50.0)  # floor to prevent unrealistic values
            prices.append((d, round(p, 4)))
        return prices

    @staticmethod
    def _rng_for(instrument_id: str) -> random.Random:
        seed = int(hashlib.sha256(instrument_id.encode()).hexdigest(), 16) % (2**32)
        return random.Random(seed)
