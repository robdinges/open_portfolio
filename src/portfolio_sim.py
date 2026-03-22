"""
Portfolio Simulatie (OpenPortfolio)
Deze script demonstreert het opzetten van een eenvoudige portefeuille, het toevoegen van producten, cash accounts en het uitvoeren van transacties met de OpenPortfolio library.
"""
from open_portfolio import *
from open_portfolio.enums import AccountType, PaymentFrequency
from datetime import date
import logging

# Logging minimaliseren
logging.basicConfig(level=logging.ERROR)

# Initieer kernobjecten
time_travel = TimeTravel()
product_collection = ProductCollection()
transaction_manager = TransactionManager()
currency_prices = CurrencyPrices()

# Maak een client en portefeuille aan
client = Client(client_id=1, name="John Doe")
portfolio = client.add_portfolio(portfolio_id=1, default_currency='EUR', cost_in_transaction_currency=True)
portfolio_analytics = PortfolioAnalytics(portfolio)

# Toon bestaande cash accounts
print("Bestaande cash accounts in de portefeuille:")
for key, account in portfolio.cash_accounts.items():
    print(f"  Account ID: {key[0]}, Valuta: {key[1]}, Type: {key[2].name}, Saldo: {account.get_balance(date.today()):,.2f}")

# Voeg cash accounts toe, alleen als ze nog niet bestaan
try:
    portfolio.add_cash_account(account_id=1, account_type=AccountType.CASH, start_balance=5000, currency='EUR')
except ValueError as e:
    print(f"[WAARSCHUWING] {e}")
try:
    portfolio.add_cash_account(account_id=2, account_type=AccountType.CASH, start_balance=2000, currency='USD')
except ValueError as e:
    print(f"[WAARSCHUWING] {e}")

# Voeg producten toe
bond = Bond(instrument_id=101, description="NL GOV 5% 2024", minimum_purchase_value=1000, smallest_trading_unit=1000, issue_currency='EUR', start_date=date(2024, 1, 1), maturity_date=date(2024, 12, 31), interest_rate=0.05, interest_payment_frequency=PaymentFrequency.YEAR)
stock = Stock(product_id=201, description="Apple Inc.", minimum_purchase_value=1, smallest_trading_unit=1, issue_currency='USD')
product_collection.add_product(bond)
product_collection.add_product(stock)

# Voeg prijzen toe
currency_prices.add_price('USD', date(2024,1,1), 0.9250)
currency_prices.add_price('EUR', date(2024,1,1), 1.0)
