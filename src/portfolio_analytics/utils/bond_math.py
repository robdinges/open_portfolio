"""Bond math helpers used by the modular analytics service."""

from __future__ import annotations

import calendar
from datetime import date
from typing import Iterable

import numpy as np


def add_months(d: date, months: int) -> date:
    """Add months while preserving end-of-month behavior when possible."""
    month_index = (d.month - 1) + months
    year = d.year + month_index // 12
    month = (month_index % 12) + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def yearfrac(start: date, end: date, convention: str = "ACT/ACT") -> float:
    """Return year fraction between two dates for a limited convention set."""
    convention = convention.upper()
    if convention == "30/360":
        start_day = 30 if start.day == 31 else start.day
        end_day = end.day
        if end.day == 31 and start_day == 30:
            end_day = 30
        return (
            (end.year - start.year) * 360
            + (end.month - start.month) * 30
            + (end_day - start_day)
        ) / 360.0
    year_length = 366 if _contains_leap_day(start, end) else 365
    return max((end - start).days, 0) / year_length


def coupon_schedule(settlement: date, maturity: date, frequency: int) -> list[date]:
    """Generate future coupon dates up to maturity inclusive."""
    if frequency <= 0:
        return [maturity]
    months = 12 // frequency
    current = maturity
    dates: list[date] = []
    while current > settlement:
        dates.append(current)
        current = add_months(current, -months)
    return sorted(dates)


def last_next_coupon(settlement: date, maturity: date, frequency: int) -> tuple[date, date]:
    """Return the last and next coupon dates around settlement."""
    if frequency <= 0:
        return maturity, maturity
    months = 12 // frequency
    current = maturity
    while current > settlement:
        previous = add_months(current, -months)
        if previous <= settlement:
            return previous, current
        current = previous
    return maturity, maturity


def accrued_interest(
    settlement: date,
    maturity: date,
    coupon_rate_pct: float,
    face_value: float,
    frequency: int,
    convention: str = "ACT/ACT",
) -> float:
    """Calculate accrued interest using coupon dates around settlement."""
    if settlement >= maturity or coupon_rate_pct <= 0 or face_value <= 0:
        return 0.0
    last_coupon, next_coupon = last_next_coupon(settlement, maturity, max(frequency, 1))
    period_fraction = yearfrac(last_coupon, next_coupon, convention)
    accrued_fraction = yearfrac(last_coupon, settlement, convention)
    if period_fraction <= 0:
        return 0.0
    coupon_amount = face_value * (coupon_rate_pct / 100.0) / max(frequency, 1)
    return coupon_amount * (accrued_fraction / period_fraction)


def simplified_ytm(
    clean_price_pct: float,
    coupon_rate_pct: float,
    years_to_maturity: float,
    face_value: float = 100.0,
) -> float:
    """Approximate yield-to-maturity suitable for a lightweight MVP."""
    if clean_price_pct <= 0 or years_to_maturity <= 0:
        return 0.0
    annual_coupon = face_value * (coupon_rate_pct / 100.0)
    clean_price = face_value * (clean_price_pct / 100.0)
    numerator = annual_coupon + ((face_value - clean_price) / years_to_maturity)
    denominator = (face_value + clean_price) / 2
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def solve_ytm_from_clean_price(
    settlement: date,
    maturity: date,
    clean_price_pct: float,
    coupon_rate_pct: float,
    frequency: int,
    face_value: float = 100.0,
    convention: str = "ACT/ACT",
    max_iter: int = 100,
    tolerance: float = 1e-8,
) -> float:
    """
    Solve YTM from clean price using discounted coupon cash flows.

    This uses a bisection method over a broad annual-yield range to provide
    stable convergence for typical bond inputs.
    """
    if settlement >= maturity or clean_price_pct <= 0 or face_value <= 0:
        return 0.0

    coupon_rate_pct = max(coupon_rate_pct, 0.0)
    frequency = max(frequency, 1)
    accrued = accrued_interest(
        settlement=settlement,
        maturity=maturity,
        coupon_rate_pct=coupon_rate_pct,
        face_value=face_value,
        frequency=frequency,
        convention=convention,
    )
    target_dirty = (face_value * clean_price_pct / 100.0) + accrued

    low = -0.95
    high = 2.0
    f_low = _price_error(settlement, maturity, coupon_rate_pct, low, frequency, face_value, target_dirty)
    f_high = _price_error(settlement, maturity, coupon_rate_pct, high, frequency, face_value, target_dirty)

    if abs(f_low) < tolerance:
        return low
    if abs(f_high) < tolerance:
        return high

    if f_low * f_high > 0:
        return simplified_ytm(
            clean_price_pct=clean_price_pct,
            coupon_rate_pct=coupon_rate_pct,
            years_to_maturity=max((maturity - settlement).days / 365.0, 0.01),
            face_value=face_value,
        )

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = _price_error(
            settlement, maturity, coupon_rate_pct, mid, frequency, face_value, target_dirty
        )
        if abs(f_mid) < tolerance:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2.0


def xirr(cash_flows: Iterable[tuple[date, float]], guess: float = 0.08) -> float:
    """Compute annualized money-weighted return from dated cash flows."""
    flows = sorted(cash_flows, key=lambda item: item[0])
    if len(flows) < 2:
        return 0.0
    amounts = [amount for _, amount in flows]
    if not any(amount > 0 for amount in amounts) or not any(amount < 0 for amount in amounts):
        return 0.0

    t0 = flows[0][0]
    year_fractions = [(d - t0).days / 365.0 for d, _ in flows]

    def npv(rate: float) -> float:
        if rate <= -0.9999:
            return float("inf")
        return sum(amount / ((1.0 + rate) ** t) for amount, t in zip(amounts, year_fractions))

    low, high = -0.95, 3.0
    f_low, f_high = npv(low), npv(high)
    if f_low * f_high > 0:
        return _newton_xirr(npv, guess)

    for _ in range(120):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-8:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def _price_error(
    settlement: date,
    maturity: date,
    coupon_rate_pct: float,
    ytm: float,
    frequency: int,
    face_value: float,
    target_dirty_price: float,
) -> float:
    schedule = coupon_schedule(settlement, maturity, max(frequency, 1))
    if not schedule:
        return -target_dirty_price
    coupon = face_value * (coupon_rate_pct / 100.0) / max(frequency, 1)
    period_rate = ytm / max(frequency, 1)
    dirty = 0.0
    for idx, pay_date in enumerate(schedule, start=1):
        cash_flow = coupon + (face_value if pay_date == maturity else 0.0)
        discount = (1 + period_rate) ** idx if period_rate > -1 else 1.0
        dirty += cash_flow / discount
    return dirty - target_dirty_price


def _newton_xirr(npv_fn, guess: float) -> float:
    rate = guess
    for _ in range(80):
        fx = npv_fn(rate)
        if abs(fx) < 1e-8:
            return rate
        h = 1e-6
        dfx = (npv_fn(rate + h) - npv_fn(rate - h)) / (2 * h)
        if abs(dfx) < 1e-12:
            break
        rate_next = rate - fx / dfx
        if rate_next <= -0.9999 or not np.isfinite(rate_next):
            break
        rate = rate_next
    return rate


def macaulay_duration(
    settlement: date,
    maturity: date,
    coupon_rate_pct: float,
    ytm: float,
    frequency: int,
    face_value: float = 100.0,
) -> float:
    """Compute Macaulay duration from discounted coupon cash flows."""
    schedule = coupon_schedule(settlement, maturity, max(frequency, 1))
    if not schedule:
        return 0.0
    coupon = face_value * (coupon_rate_pct / 100.0) / max(frequency, 1)
    period_rate = ytm / max(frequency, 1)
    weighted_sum = 0.0
    pv_total = 0.0
    for index, pay_date in enumerate(schedule, start=1):
        cash_flow = coupon + (face_value if pay_date == maturity else 0.0)
        discount = (1 + period_rate) ** index if period_rate > -1 else 1.0
        present_value = cash_flow / discount
        time_years = yearfrac(settlement, pay_date, "ACT/ACT")
        weighted_sum += time_years * present_value
        pv_total += present_value
    if pv_total <= 0:
        return 0.0
    return weighted_sum / pv_total


def modified_duration(macaulay: float, ytm: float, frequency: int) -> float:
    """Compute modified duration from Macaulay duration."""
    periods = max(frequency, 1)
    return macaulay / (1 + (ytm / periods)) if periods > 0 else macaulay


def convexity(
    settlement: date,
    maturity: date,
    coupon_rate_pct: float,
    ytm: float,
    frequency: int,
    face_value: float = 100.0,
) -> float:
    """Compute a simple bond convexity measure from discounted cash flows."""
    schedule = coupon_schedule(settlement, maturity, max(frequency, 1))
    if not schedule:
        return 0.0
    coupon = face_value * (coupon_rate_pct / 100.0) / max(frequency, 1)
    period_rate = ytm / max(frequency, 1)
    numerator = 0.0
    denominator = 0.0
    for index, pay_date in enumerate(schedule, start=1):
        cash_flow = coupon + (face_value if pay_date == maturity else 0.0)
        discount = (1 + period_rate) ** index if period_rate > -1 else 1.0
        present_value = cash_flow / discount
        time_years = yearfrac(settlement, pay_date, "ACT/ACT")
        numerator += present_value * time_years * (time_years + (1 / max(frequency, 1)))
        denominator += present_value
    if denominator <= 0:
        return 0.0
    scale = (1 + period_rate) ** 2 if period_rate > -1 else 1.0
    return numerator / (denominator * scale)


def _contains_leap_day(start: date, end: date) -> bool:
    for year in range(start.year, end.year + 1):
        if calendar.isleap(year):
            leap_day = date(year, 2, 29)
            if start <= leap_day <= end:
                return True
    return False
