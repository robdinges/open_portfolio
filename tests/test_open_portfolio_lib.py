# test_open_portfolio_lib.py
import unittest
from datetime import date, timedelta
from src.OpenPortfolioLib import (
    TimeTravel, Client, Portfolio, AccountType, MovementType,
    ProductCollection, Product, InstrumentType, TransactionManager,
    TransactionTemplate
)

class TestTimeTravel(unittest.TestCase):
    def setUp(self):
        self.time_travel = TimeTravel()

    def test_skip_days(self):
        initial_date = self.time_travel.current_date
        new_date = self.time_travel.skip_days(5)
        self.assertEqual(new_date, initial_date + timedelta(days=5))

    def test_skip_working_days(self):
        initial_date = self.time_travel.current_date
        new_date = self.time_travel.skip_working_days(5)
        # Assuming initial_date is a weekday
        self.assertEqual(new_date, initial_date + timedelta(days=7))  # 5 working days is 7 calendar days if starting on a Monday

class TestClientPortfolio(unittest.TestCase):
    def setUp(self):
        self.client = Client(1, "Test Client")

    def test_add_portfolio(self):
        portfolio = self.client.add_portfolio(1)
        self.assertEqual(portfolio.portfolio_id, 1)
        self.assertEqual(portfolio.client_id, self.client.client_id)

class TestPortfolioCalculations(unittest.TestCase):
    def setUp(self):
        self.client = Client(1, "Test Client")
        self.portfolio = self.client.add_portfolio(1)
        self.product_collection = ProductCollection()

        # Add a product to the collection
        self.product = Product(1, "Test Stock", InstrumentType.STOCK, 100, 1, 'EUR')
        self.product_collection.add_product(self.product)

        # Create a TransactionManager
        self.transaction_manager = TransactionManager()

        # Ensure the initial cash account has sufficient balance
        account_key = (self.portfolio.portfolio_id, 'EUR', AccountType.CASH)
        if account_key in self.portfolio.cash_accounts:
            self.portfolio.cash_accounts[account_key].balance = 1000
        else:
            self.portfolio.add_cash_account(1, start_balance=1000)

    def test_calculate_return(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        # Add transactions to the portfolio to simulate returns
        transaction = self.transaction_manager.create_transaction(
            transaction_date=start_date,
            portfolio_id=self.portfolio.portfolio_id,
            template=TransactionTemplate.BUY,
            account_id=1,
            product_id=self.product.instrument_id,
            amount=10,
            price=10
        )
        self.portfolio.execute_transaction(transaction, self.product_collection)

        # Calculate the return
        returns = self.portfolio.calculate_return(start_date, end_date)
        self.assertIsInstance(returns, list)

if __name__ == '__main__':
    unittest.main()