import pytest
from datetime import timedelta, date
from src.OpenPortfolioLib import TimeTravel, PaymentFrequency, Bond

class TestAccruedInterest:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.time_travel = TimeTravel()

    def create_bond(self):
        return Bond(
            instrument_id=999,
            description='description',
            minimum_purchase_value=1,
            smallest_trading_unit=1,
            issue_currency='EUR',
            start_date=date(2024, 1, 1),
            maturity_date=date(2026, 1, 1),
            interest_rate=0.03,
            interest_payment_frequency=PaymentFrequency.YEAR
        )

    def test_accrued_interest(self):
        new_bond = self.create_bond()
        nominal_value = 100000
        valuation_date = date(2024, 12, 31)
        accrued_interest = new_bond.calculate_accrued_interest(nominal_value, self.time_travel, valuation_date)
        assert accrued_interest == 3000

class TestTimeTravel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.time_travel = TimeTravel()

    def test_skip_days(self):
        initial_date = self.time_travel.current_date
        new_date = self.time_travel.skip_days(5)
        assert new_date == initial_date + timedelta(days=5)

    def test_skip_working_days(self):
        initial_date = self.time_travel.current_date
        new_date = self.time_travel.skip_working_days(5)

        # Tel het aantal kalenderdagen om 5 werkdagen over te slaan
        days_skipped = 0
        while days_skipped < 5:
            initial_date += timedelta(days=1)
            if not self.time_travel.is_weekend(initial_date):
                days_skipped += 1

        assert new_date == initial_date