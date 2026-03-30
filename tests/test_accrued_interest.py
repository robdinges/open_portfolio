import pytest
from datetime import date

from open_portfolio.products import Bond
from open_portfolio.enums import PaymentFrequency, InterestType


@pytest.fixture
def sample_bond() -> Bond:
    """Bond: 5% annual coupon, start 2024-01-01, maturity 2034-01-01."""
    return Bond(
        instrument_id=1,
        description="Test Bond 5%",
        minimum_purchase_value=1000.0,
        smallest_trading_unit=1.0,
        issue_currency="EUR",
        start_date=date(2024, 1, 1),
        maturity_date=date(2034, 1, 1),
        interest_rate=0.05,
        interest_payment_frequency=PaymentFrequency.YEAR,
    )


@pytest.fixture
def bond_non_leap() -> Bond:
    """Bond starting in a non-leap year (2023)."""
    return Bond(
        instrument_id=2,
        description="Non-leap Bond 3%",
        minimum_purchase_value=1000.0,
        smallest_trading_unit=1.0,
        issue_currency="EUR",
        start_date=date(2023, 1, 1),
        maturity_date=date(2033, 1, 1),
        interest_rate=0.03,
        interest_payment_frequency=PaymentFrequency.YEAR,
    )


# ── ACT/ACT success cases ──────────────────────────────────────────────


class TestActActAccruedInterest:
    def test_standard_period_leap_year(self, sample_bond: Bond):
        """2024 is a leap year; 91 days from Jan 1 to Apr 1."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 4, 1),
            interest_type=InterestType.ACT_ACT,
        )
        expected = 100_000 * 0.05 * 91 / 366
        assert result == pytest.approx(expected, rel=1e-9)

    def test_standard_period_non_leap_year(self, bond_non_leap: Bond):
        """2023 is not a leap year; 90 days from Jan 1 to Apr 1."""
        result = bond_non_leap.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2023, 4, 1),
            interest_type=InterestType.ACT_ACT,
        )
        expected = 100_000 * 0.03 * 90 / 365
        assert result == pytest.approx(expected, rel=1e-9)

    def test_full_year_leap(self, sample_bond: Bond):
        """Full year 2024 (leap): 366 days."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2025, 1, 1),
            interest_type=InterestType.ACT_ACT,
        )
        expected = 100_000 * 0.05 * 366 / 366
        assert result == pytest.approx(expected, rel=1e-9)

    def test_default_interest_type_is_act_act(self, sample_bond: Bond):
        """Omitting interest_type should default to ACT_ACT."""
        explicit = sample_bond.calculate_accrued_interest(
            nominal_value=50_000,
            valuation_date=date(2024, 7, 1),
            interest_type=InterestType.ACT_ACT,
        )
        default = sample_bond.calculate_accrued_interest(
            nominal_value=50_000,
            valuation_date=date(2024, 7, 1),
        )
        assert default == pytest.approx(explicit, rel=1e-12)


# ── 30/360 success cases ───────────────────────────────────────────────


class TestThirty360AccruedInterest:
    def test_standard_period(self, sample_bond: Bond):
        """Jan 1 -> Apr 1 = 3 months x 30 = 90 days in 30/360."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 4, 1),
            interest_type=InterestType.THIRTY_360,
        )
        expected = 100_000 * 0.05 * 90 / 360
        assert result == pytest.approx(expected, rel=1e-9)

    def test_cross_year_period(self, sample_bond: Bond):
        """Jan 1 2024 -> Jan 1 2025 = 360 days in 30/360."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2025, 1, 1),
            interest_type=InterestType.THIRTY_360,
        )
        expected = 100_000 * 0.05 * 360 / 360
        assert result == pytest.approx(expected, rel=1e-9)

    def test_mid_month(self, sample_bond: Bond):
        """Jan 1 -> Mar 15 = 2x30 + 14 = 74 days."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 3, 15),
            interest_type=InterestType.THIRTY_360,
        )
        expected = 100_000 * 0.05 * 74 / 360
        assert result == pytest.approx(expected, rel=1e-9)

    def test_same_month_different_day(self, sample_bond: Bond):
        """Jan 1 -> Jan 20 = 19 days."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 1, 20),
            interest_type=InterestType.THIRTY_360,
        )
        expected = 100_000 * 0.05 * 19 / 360
        assert result == pytest.approx(expected, rel=1e-9)


# ── Edge cases ──────────────────────────────────────────────────────────


class TestAccruedInterestEdgeCases:
    def test_valuation_equals_start_date(self, sample_bond: Bond):
        """Zero days elapsed -> zero accrued interest."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 1, 1),
        )
        assert result == pytest.approx(0.0)

    def test_valuation_equals_start_date_thirty_360(self, sample_bond: Bond):
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 1, 1),
            interest_type=InterestType.THIRTY_360,
        )
        assert result == pytest.approx(0.0)

    def test_zero_nominal_value(self, sample_bond: Bond):
        result = sample_bond.calculate_accrued_interest(
            nominal_value=0.0,
            valuation_date=date(2024, 6, 1),
        )
        assert result == pytest.approx(0.0)

    def test_zero_interest_rate(self):
        bond = Bond(
            instrument_id=99,
            description="Zero coupon",
            minimum_purchase_value=1000.0,
            smallest_trading_unit=1.0,
            issue_currency="EUR",
            start_date=date(2024, 1, 1),
            maturity_date=date(2034, 1, 1),
            interest_rate=0.0,
            interest_payment_frequency=PaymentFrequency.YEAR,
        )
        result = bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 6, 1),
        )
        assert result == pytest.approx(0.0)

    def test_negative_days_valuation_before_start(self, sample_bond: Bond):
        """Valuation before start date produces negative accrued interest."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2023, 12, 1),
        )
        assert result < 0

    def test_negative_days_thirty_360(self, sample_bond: Bond):
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2023, 12, 1),
            interest_type=InterestType.THIRTY_360,
        )
        assert result < 0

    def test_one_day_accrued(self, sample_bond: Bond):
        """Single day of accrued interest."""
        result = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 1, 2),
        )
        # Jan 1 -> Jan 2: no Feb 29 in range -> denominator 365
        expected = 100_000 * 0.05 * 1 / 365
        assert result == pytest.approx(expected, rel=1e-9)

    def test_large_nominal_value(self, sample_bond: Bond):
        result = sample_bond.calculate_accrued_interest(
            nominal_value=1_000_000_000,
            valuation_date=date(2024, 7, 1),
            interest_type=InterestType.THIRTY_360,
        )
        days = 6 * 30  # 180 days
        expected = 1_000_000_000 * 0.05 * days / 360
        assert result == pytest.approx(expected, rel=1e-9)

    def test_act_act_vs_thirty_360_differ(self, sample_bond: Bond):
        """ACT/ACT and 30/360 should generally produce different results."""
        act = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 3, 15),
            interest_type=InterestType.ACT_ACT,
        )
        t360 = sample_bond.calculate_accrued_interest(
            nominal_value=100_000,
            valuation_date=date(2024, 3, 15),
            interest_type=InterestType.THIRTY_360,
        )
        assert act > 0
        assert t360 > 0
        assert act != pytest.approx(t360, rel=1e-6)
