"""Generate a realistic multi-portfolio dataset for testing and demo purposes.

This module creates a complete sample with multiple clients, portfolios,
products (stocks and bonds), and a history of realistic transactions
spanning several months.

Usage example::

    from open_portfolio.sample_data import create_realistic_dataset

    db = Database("demo.sqlite")
    dataset = create_realistic_dataset()
    
    for client in dataset['clients']:
        db.add_client(client)
    for portfolio in dataset['portfolios']:
        db.add_portfolio(portfolio)
"""


import json
import os
from datetime import date, datetime
from .clients import Client
from .enums import TransactionTemplate, PaymentFrequency
from .products import Stock, Bond
from .product_collection import ProductCollection
from .prices import CurrencyPrices
from .transactions import TransactionManager


def create_realistic_dataset():
    """
    Create a comprehensive multi-portfolio dataset with:
    - 2 clients (Alice and Bob)
    - 3 portfolios (Alice: 2, Bob: 1)
    - 8 products (5 stocks, 3 bonds, mixed currencies)
    - 30+ realistic transactions spanning 6 months
    - Currency conversions and multiple account types
    
    Returns:
        dict: Contains 'clients', 'portfolios', 'products', 'prices', 'transactions'
    """

    # Pad naar data directory
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')

    # ...existing code...
    """
    Create a comprehensive multi-portfolio dataset with:
    - 2 clients (Alice and Bob)
    - 3 portfolios (Alice: 2, Bob: 1)
    - 8 products (5 stocks, 3 bonds, mixed currencies)
    - 30+ realistic transactions spanning 6 months
    - Currency conversions and multiple account types
    
    Returns:
        dict: Contains 'clients', 'portfolios', 'products', 'prices', 'transactions'
    """

    # Pad naar data directory
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')

    # Load clients
    with open(os.path.join(data_dir, 'clients.json')) as f:
        clients_data = json.load(f)
    clients = [Client(client_id=c['client_id'], name=c['name']) for c in clients_data]

    # Load portfolios
    with open(os.path.join(data_dir, 'portfolios.json')) as f:
        portfolios_data = json.load(f)
    portfolios = []
    for p in portfolios_data:
        client = next(c for c in clients if c.client_id == p['client_id'])
        portfolios.append(
            client.add_portfolio(
                portfolio_id=p['portfolio_id'],
                default_currency=p['default_currency'],
                name=p.get('name', f"Portfolio {p['portfolio_id']}")
            )
        )

    # Load products
    with open(os.path.join(data_dir, 'products.json')) as f:
        products_data = json.load(f)
    pc = ProductCollection()
    products = []

    for prod in products_data:
        if prod['type'] == 'stock':
            stock = Stock(
                product_id=prod['product_id'],
                description=prod.get('name', ""),
                minimum_purchase_value=prod['minimum_purchase_value'],
                smallest_trading_unit=prod['smallest_trading_unit'],
                issue_currency=prod['issue_currency']
            )
            stock.instrument_id = prod['product_id']
            pc.add_product(stock)
            products.append(stock)
        elif prod['type'] == 'bond':
            bond = Bond(
                instrument_id=prod['product_id'],
                description=prod.get('name', ""),
                minimum_purchase_value=prod['minimum_purchase_value'],
                smallest_trading_unit=prod['smallest_trading_unit'],
                issue_currency=prod['issue_currency'],
                start_date=datetime.strptime(prod['start_date'], "%Y-%m-%d").date(),
                maturity_date=datetime.strptime(prod['maturity_date'], "%Y-%m-%d").date(),
                interest_rate=prod['interest_rate'],
                interest_payment_frequency=PaymentFrequency[prod['interest_payment_frequency']]
            )
            pc.add_product(bond)
            products.append(bond)

    # Load and assign product prices
    with open(os.path.join(data_dir, 'prices.json')) as f:
        prices_data = json.load(f)
    prices_by_id = {p['product_id']: p['prices'] for p in prices_data}
    for product in products:
        for price_entry in prices_by_id.get(product.instrument_id, []):
            price_date = datetime.strptime(price_entry[0], "%Y-%m-%d").date()
            product.add_price(price_date, price_entry[1])

    # Load cash accounts
    with open(os.path.join(data_dir, 'cash_accounts.json')) as f:
        cash_accounts_data = json.load(f)
    for ca in cash_accounts_data:
        portfolio = next(p for p in portfolios if p.portfolio_id == ca['portfolio_id'])
        for (acct_id, curr, acc_type), account in portfolio.cash_accounts.items():
            if curr == ca['currency']:
                account.balance = ca['balance']
                account.start_balance = ca['balance']

    # Load currency prices from JSON
    cp = CurrencyPrices()
    with open(os.path.join(data_dir, 'currency_prices.json')) as f:
        currency_prices_data = json.load(f)
    for entry in currency_prices_data:
        currency = entry['currency']
        counter_currency = entry.get('counter_currency', 'EUR')
        for price_entry in entry['prices']:
            price_date = datetime.strptime(price_entry[0], "%Y-%m-%d").date()
            cp.add_price(currency, price_date, price_entry[1], counter_currency)

    # Load transactions
    with open(os.path.join(data_dir, 'transactions.json')) as f:
        transactions_data = json.load(f)
    tm = TransactionManager()
    transactions = []
    for tx in transactions_data:
        portfolio = next(p for p in portfolios if p.portfolio_id == tx['portfolio_id'])
        t = tm.create_and_execute_transaction(
            transaction_date=datetime.strptime(tx['transaction_date'], "%Y-%m-%d").date(),
            portfolio_id=tx['portfolio_id'],
            template=TransactionTemplate[tx['template']],
            portfolio=portfolio,
            product_collection=pc,
            currency_prices=cp,
            product_id=tx.get('product_id'),
            amount=tx.get('amount'),
            price=tx.get('price')
        )
        transactions.append(t)

    return {
        'clients': clients,
        'portfolios': portfolios,
        'products': products,
        'prices': cp,
        'transactions': transactions
    }


if __name__ == "__main__":
    dataset = create_realistic_dataset()
    print(f"  - {len(dataset['clients'])} clients")
    print(f"  - {len(dataset['portfolios'])} portfolios")
    print(f"  - {len(dataset['products'])} products")
    print(f"  - {len(dataset['transactions'])} transactions")
