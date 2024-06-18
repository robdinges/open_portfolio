import pytest
from datetime import timedelta, date
from src.OpenPortfolioLib import *

class TestTransactions:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.initialize_components()
        self.setup_client_and_portfolio()
        self.setup_cash_account()
        self.setup_test_bond()
        self.setup_bond_prices()
        self.execute_initial_transaction()

    def initialize_components(self):
        """Initialize core components."""
        self.time_travel = TimeTravel()
        self.product_collection = ProductCollection()
        self.transaction_manager = TransactionManager()

    def setup_client_and_portfolio(self):
        """Setup client and their portfolio."""
        self.client = Client(client_id=999, name="John Doe")
        self.portfolio = self.client.add_portfolio(portfolio_id=999)
        self.portfolio.cash_accounts[(self.portfolio.portfolio_id, 'EUR', AccountType.CASH)].balance = 10000

    def setup_cash_account(self):
        """Add a cash account to the portfolio."""
        self.portfolio.add_cash_account(account_id=999, start_balance=10000, currency='USD')

    def setup_test_bond(self):
        """Create and add a bond to the product collection."""
        self.test_bond = Bond(
            instrument_id=999,
            description='description',
            minimum_purchase_value=1,
            smallest_trading_unit=1,
            issue_currency='EUR',
            start_date=date(2024, 1, 1),
            maturity_date=date(2025, 1, 1),
            interest_rate=0.03,
            interest_payment_frequency=PaymentFrequency.YEAR
        )
        self.product_collection.add_product(self.test_bond)

    def setup_bond_prices(self):
        """Add historical prices for the bond."""
        self.currency_prices = CurrencyPrices()
        prices = {
            date(2022, 1, 1): 100.0,
            date(2022, 2, 1): 101.0,
            date(2022, 3, 1): 102.0,
            date(2022, 4, 1): 103.0
        }
        for price_date, price_value in prices.items():
            self.currency_prices.add_price('USD', price_date, price_value)

    def execute_initial_transaction(self):
        """Create and execute an initial bond purchase transaction."""
        self.transaction_manager.create_and_execute_transaction(
            transaction_date=date(2024, 7, 2),
            portfolio_id=self.portfolio.portfolio_id,
            template=TransactionTemplate.BUY,
            portfolio=self.portfolio,
            product_collection=self.product_collection,
            currency_prices = self.currency_prices,
            product_id=999,
            amount=1000,
            price=1.0,
            # cost=10
        )

    def test_accrued_interest(self):
        """Test the calculation of accrued interest."""
        nominal_value = 1000
        valuation_date = date(2024, 7, 2)
        accrued_interest = self.test_bond.calculate_accrued_interest(nominal_value, self.time_travel, valuation_date)
        assert accrued_interest == 15

    def test_transaction_values(self):
        """Test the values of the transactions in the portfolio."""
        transactions = self.portfolio.list_all_transactions()
        #for cash_movement in transaction[0].cash_movements:
        #    if cash_movement['amount']
        cash_movement = transactions[0]['cash_movements']
        security_movement = transactions[0]['security_movements']
        assert transactions[0]['account_id'] == 999
        assert cash_movement[0]['amount'] == -1000  # buy amount
        assert cash_movement[1]['amount'] == -10 # costs
        assert cash_movement[2]['amount'] == -15  #acccrued interest
        assert security_movement[0]['amount_nominal'] == 1000  # shares/nominal value


class TestTimeTravel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.time_travel = TimeTravel()

    def test_skip_days(self):
        """Test skipping a specific number of calendar days."""
        initial_date = self.time_travel.current_date
        new_date = self.time_travel.skip_days(5)
        assert new_date == initial_date + timedelta(days=5)

    def test_skip_working_days(self):
        """Test skipping a specific number of working days."""
        initial_date = self.time_travel.current_date
        new_date = self.time_travel.skip_working_days(5)

        # Count the number of calendar days to skip 5 working days
        days_skipped = 0
        current_date = initial_date
        while days_skipped < 5:
            current_date += timedelta(days=1)
            if not self.time_travel.is_weekend(current_date):
                days_skipped += 1

        assert new_date == current_date