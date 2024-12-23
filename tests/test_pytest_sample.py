import pytest
import logging
from datetime import date
from src.OpenPortfolioLib import *

@pytest.fixture(autouse=True)
def setup():
    # Initialize logging
    logging.basicConfig(level=logging.ERROR)

    # Initialize the necessary objects
    time_travel = TimeTravel()
    product_collection = ProductCollection()
    transaction_manager = TransactionManager()
    currency_prices = CurrencyPrices()

    # Create a client
    client = Client(client_id=10, name="Rob van der Erve")

    # Add a portfolio to the client
    portfolio10 = client.add_portfolio(portfolio_id=10, default_currency='EUR', cost_in_transaction_currency=True)
    portfolio10.cash_accounts[(portfolio10.portfolio_id, 'EUR', AccountType.CASH)].balance = 1_000
    portfolio10.add_cash_account(account_id=10, account_type=AccountType.CASH, start_balance=1_000, currency='USD')

    # bond 1
    bond1 = Bond(instrument_id=201, description="NL GOV 5% 2024", minimum_purchase_value=1000, smallest_trading_unit=1000, issue_currency='EUR', start_date=date(2024, 1, 1), maturity_date=date(2024, 12, 31), interest_rate=0.05, interest_payment_frequency=PaymentFrequency.YEAR)
    product_collection.add_product(bond1)

    # bond 2
    bond2 = Bond(instrument_id=202, description="US GOV 3% 2022-2032", minimum_purchase_value=1000, smallest_trading_unit=1000, issue_currency='GBP', start_date=date(2022, 11, 1), maturity_date=date(2032, 10, 31), interest_rate=0.03, interest_payment_frequency=PaymentFrequency.YEAR)
    product_collection.add_product(bond2)

    currency_prices.add_price('USD', date(2024,1,1), 0.9250)
    return

#7
transaction_manager.create_and_execute_transaction(
    transaction_date=date(2024, 1, 30),
    portfolio_id=portfolio10.portfolio_id,
    template=TransactionTemplate.BUY,
    portfolio=portfolio10,
    product_collection=product_collection,
    currency_prices=currency_prices,
    product_id=201,
    amount=1000,
    price=.8,
)

#8
transaction_manager.create_and_execute_transaction(
    transaction_date=date(2025, 1, 15),
    portfolio_id=portfolio10.portfolio_id,
    template=TransactionTemplate.BUY,
    portfolio=portfolio10,
    product_collection=product_collection,
    currency_prices=currency_prices,
    product_id=201,
    amount=1000,
    price=.9805,
)
