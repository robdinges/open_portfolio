import pytest
from datetime import timedelta, date
from src.OpenPortfolioLib import TimeTravel, PaymentFrequency, Bond

# Fixture to create a bond
@pytest.fixture
def create_bond():
    new_bond = Bond(
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
    return new_bond

# Test function using the fixture
def test_accrued_interest(create_bond):
    nominal_value = 100000
    time_travel = TimeTravel()
    valuation_date = date(2024, 12, 31)
    accrued_interest = create_bond.calculate_accrued_interest(nominal_value, time_travel, valuation_date)
    assert accrued_interest == 3000

# Test class using pytest
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
        # Assuming initial_date is a weekday
        assert new_date == initial_date + timedelta(days=7)  # 5 working days is 7 calendar days if starting on a Monday
        