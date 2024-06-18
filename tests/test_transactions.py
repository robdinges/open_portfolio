import pytest
from datetime import timedelta, date
from src.OpenPortfolioLib import *

class TestTransactions:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.initialize_components()
        self.setup_client_and_portfolio()
        self.setup_cash_accounts()
        self.setup_test_instruments()
        self.setup_instrument_prices()
    
    def initialize_components(self):
        """Initialize core components."""
        self.time_travel = TimeTravel()
        self.product_collection = ProductCollection()
        self.transaction_manager = TransactionManager()
        self.currency_prices = CurrencyPrices()
        self.currency_prices.add_price('USD', date.today(), 1.10)  # Assuming EUR is the base currency

    def setup_client_and_portfolio(self):
        """Setup client and their portfolio."""
        self.client = Client(client_id=999, name="John Doe")
        self.portfolio = self.client.add_portfolio(portfolio_id=999)
        self.portfolio.cash_accounts[(self.portfolio.portfolio_id, 'EUR', AccountType.CASH)].balance = 10000

    def setup_cash_accounts(self):
        """Add cash accounts to the portfolio."""
        #self.portfolio.add_cash_account(account_id=999, currency='EUR', start_balance=10000)
        self.portfolio.add_cash_account(account_id=999, currency='USD', start_balance=5000)

    def setup_test_instruments(self):
        """Create and add instruments to the product collection."""
        self.test_stock = Stock(
            product_id=1001,
            description='USD Stock',
            minimum_purchase_value=1,
            smallest_trading_unit=1,
            issue_currency='USD'
        )
        self.test_bond = Bond(
            instrument_id=1002,
            description='EUR Bond',
            minimum_purchase_value=1000,
            smallest_trading_unit=1,
            issue_currency='EUR',
            start_date=date(2024, 1, 1),
            maturity_date=date(2034, 1, 1),
            interest_rate=0.03,
            interest_payment_frequency=PaymentFrequency.YEAR
        )
        self.product_collection.add_product(self.test_stock)
        self.product_collection.add_product(self.test_bond)

    def setup_instrument_prices(self):
        """Add historical prices for the instruments."""
        self.test_stock.add_price(date(2024, 1, 1), 123.45)
        self.test_stock.add_price(date(2024, 4, 1), 138.12)
        self.test_bond.add_price(date(2024, 1, 1), 101.0)
        self.test_bond.add_price(date(2024, 10, 1), 102.0)

    def test_stock_transaction(self):
        """Test buying and selling stock transactions."""
        # Buy 10 stocks at 123.45 USD
        self.transaction_manager.create_and_execute_transaction(
            transaction_date=date(2024, 1, 1),
            portfolio_id=self.portfolio.portfolio_id,
            template=TransactionTemplate.BUY,
            portfolio=self.portfolio,
            product_collection=self.product_collection,
            currency_prices=self.currency_prices,
            product_id=1001,
            amount=10,
            price=123.45
        )

        # Sell 4 stocks at 138.12 USD after 3 months
        self.transaction_manager.create_and_execute_transaction(
            transaction_date=date(2024, 4, 1),
            portfolio_id=self.portfolio.portfolio_id,
            template=TransactionTemplate.SELL,
            portfolio=self.portfolio,
            product_collection=self.product_collection,
            currency_prices=self.currency_prices,
            product_id=1001,
            amount=4,
            price=138.12
        )

        transactions = self.portfolio.list_all_transactions()
        assert transactions[0]['cash_movements'][0]['amount'] == -1234.50  # Buy amount in USD
        assert transactions[1]['cash_movements'][0]['amount'] == 552.48  # Sell amount in USD

    def test_bond_transaction(self):
        """Test buying and selling bond transactions."""
        # Buy bond at 101%
        self.transaction_manager.create_and_execute_transaction(
            transaction_date=date(2024, 1, 1),
            portfolio_id=self.portfolio.portfolio_id,
            template=TransactionTemplate.BUY,
            portfolio=self.portfolio,
            product_collection=self.product_collection,
            currency_prices=self.currency_prices,
            product_id=1002,
            amount=3000,
            price=1.01
        )

        # Sell part of the bond after 9 months at 102%
        self.transaction_manager.create_and_execute_transaction(
            transaction_date=date(2024, 10, 1),
            portfolio_id=self.portfolio.portfolio_id,
            template=TransactionTemplate.SELL,
            portfolio=self.portfolio,
            product_collection=self.product_collection,
            currency_prices=self.currency_prices,
            product_id=1002,
            amount=1000,
            price=1.02
        )

        transactions = self.portfolio.list_all_transactions()
        #print("Transactions:", transactions)
        for a in transactions:
            print(a['cash_movements'][1]['amount'])

        # Controleer of de transacties correct zijn uitgevoerd en geregistreerd
        assert len(transactions) >= 2  # Zorg ervoor dat er minstens 4 transacties zijn

        assert transactions[0]['cash_movements'][0]['amount'] == -3030  # Buy amount in EUR
        assert transactions[1]['cash_movements'][0]['amount'] == 1020  # Sell amount in EUR

    def test_insufficient_funds(self):
        """Test rejection of transaction due to insufficient funds."""
        # Attempt to buy 100 stocks at 140.00 USD
        with pytest.raises(ValueError, match=r"Insufficient balance"):
            self.transaction_manager.create_and_execute_transaction(
                transaction_date=date(2024, 2, 1),
                portfolio_id=self.portfolio.portfolio_id,
                template=TransactionTemplate.BUY,
                portfolio=self.portfolio,
                product_collection=self.product_collection,
                currency_prices=self.currency_prices,
                product_id=1001,
                amount=10000,
                price=140.00
            )