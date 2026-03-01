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

from datetime import date, timedelta
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
    dataset = {
        'clients': [],
        'portfolios': [],
        'products': [],
        'prices': [],
        'transactions': []
    }
    
    # Create clients
    client_alice = Client(client_id=1, name="Alice Johnson")
    client_bob = Client(client_id=2, name="Bob Smith")
    dataset['clients'] = [client_alice, client_bob]
    
    # Create portfolios
    portfolio_alice_eur = client_alice.add_portfolio(portfolio_id=1, default_currency='EUR')
    portfolio_alice_usd = client_alice.add_portfolio(portfolio_id=2, default_currency='USD')
    portfolio_bob_eur = client_bob.add_portfolio(portfolio_id=3, default_currency='EUR')
    dataset['portfolios'] = [portfolio_alice_eur, portfolio_alice_usd, portfolio_bob_eur]
    
    # Create product collection
    pc = ProductCollection()
    
    # Stocks (realistic data)
    stock_apple = Stock(
        product_id=1,
        description="Apple Inc. (AAPL)",
        minimum_purchase_value=100,
        smallest_trading_unit=1,
        issue_currency='USD'
    )
    stock_google = Stock(
        product_id=2,
        description="Alphabet Inc. (GOOGL)",
        minimum_purchase_value=100,
        smallest_trading_unit=1,
        issue_currency='USD'
    )
    stock_tesla = Stock(
        product_id=3,
        description="Tesla Inc. (TSLA)",
        minimum_purchase_value=100,
        smallest_trading_unit=1,
        issue_currency='USD'
    )
    stock_microsoft = Stock(
        product_id=4,
        description="Microsoft Corp. (MSFT)",
        minimum_purchase_value=100,
        smallest_trading_unit=1,
        issue_currency='USD'
    )
    stock_siemens = Stock(
        product_id=5,
        description="Siemens AG (SIE)",
        minimum_purchase_value=50,
        smallest_trading_unit=1,
        issue_currency='EUR'
    )
    
    # Bonds
    bond_eu_gov = Bond(
        instrument_id=101,
        description="EU Government Bond 2.5%",
        minimum_purchase_value=1000,
        smallest_trading_unit=1,
        issue_currency='EUR',
        start_date=date(2020, 1, 1),
        maturity_date=date(2030, 1, 1),
        interest_rate=0.025,
        interest_payment_frequency=PaymentFrequency.YEAR
    )
    bond_corporate = Bond(
        instrument_id=102,
        description="Corporate Bond 3.5%",
        minimum_purchase_value=1000,
        smallest_trading_unit=1,
        issue_currency='EUR',
        start_date=date(2022, 6, 15),
        maturity_date=date(2027, 6, 15),
        interest_rate=0.035,
        interest_payment_frequency=PaymentFrequency.YEAR
    )
    bond_us = Bond(
        instrument_id=103,
        description="US Treasury Bond 4.0%",
        minimum_purchase_value=1000,
        smallest_trading_unit=1,
        issue_currency='USD',
        start_date=date(2023, 1, 1),
        maturity_date=date(2033, 1, 1),
        interest_rate=0.04,
        interest_payment_frequency=PaymentFrequency.YEAR
    )
    
    products = [stock_apple, stock_google, stock_tesla, stock_microsoft, stock_siemens, 
                bond_eu_gov, bond_corporate, bond_us]
    for prod in products:
        pc.add_product(prod)
    
    dataset['products'] = products
    
    # Create currency prices
    cp = CurrencyPrices()
    base_date = date(2025, 9, 1)
    
    # Stock prices (realistic progression over 6 months)
    prices = {
        stock_apple.instrument_id: [
            (date(2025, 9, 1), 210.0),
            (date(2025, 10, 15), 215.0),
            (date(2025, 11, 30), 220.0),
            (date(2025, 12, 15), 225.0),
            (date(2026, 1, 15), 230.0),
            (date(2026, 2, 28), 235.0),
            (date(2026, 3, 1), 236.0),
        ],
        stock_google.instrument_id: [
            (date(2025, 9, 1), 160.0),
            (date(2025, 10, 15), 162.0),
            (date(2025, 11, 30), 165.0),
            (date(2025, 12, 15), 168.0),
            (date(2026, 1, 15), 170.0),
            (date(2026, 2, 28), 172.0),
            (date(2026, 3, 1), 173.0),
        ],
        stock_tesla.instrument_id: [
            (date(2025, 9, 1), 250.0),
            (date(2025, 10, 15), 245.0),
            (date(2025, 11, 30), 240.0),
            (date(2025, 12, 15), 248.0),
            (date(2026, 1, 15), 255.0),
            (date(2026, 2, 28), 260.0),
            (date(2026, 3, 1), 262.0),
        ],
        stock_microsoft.instrument_id: [
            (date(2025, 9, 1), 380.0),
            (date(2025, 10, 15), 385.0),
            (date(2025, 11, 30), 390.0),
            (date(2025, 12, 15), 395.0),
            (date(2026, 1, 15), 400.0),
            (date(2026, 2, 28), 405.0),
            (date(2026, 3, 1), 407.0),
        ],
        stock_siemens.instrument_id: [
            (date(2025, 9, 1), 145.0),
            (date(2025, 10, 15), 147.0),
            (date(2025, 11, 30), 149.0),
            (date(2025, 12, 15), 151.0),
            (date(2026, 1, 15), 153.0),
            (date(2026, 2, 28), 155.0),
            (date(2026, 3, 1), 156.0),
        ],
        bond_eu_gov.instrument_id: [
            (date(2025, 9, 1), 1020.0),
            (date(2026, 3, 1), 1025.0),
        ],
        bond_corporate.instrument_id: [
            (date(2025, 9, 1), 1015.0),
            (date(2026, 3, 1), 1020.0),
        ],
        bond_us.instrument_id: [
            (date(2025, 9, 1), 1010.0),
            (date(2026, 3, 1), 1015.0),
        ]
    }
    
    for product_id, price_list in prices.items():
        for d, price in price_list:
            cp.add_price(product_id, d, price)
    
    # USD/EUR rate
    cp.add_price('USD', date(2025, 9, 1), 1.10)
    cp.add_price('USD', date(2026, 3, 1), 1.12)
    
    dataset['prices'] = cp
    
    # Initialize cash accounts
    # Portfolio automatically creates one default account; we need to set balances or add more
    for (acct_id, curr, acc_type), account in portfolio_alice_eur.cash_accounts.items():
        account.balance = 50000
        account.start_balance = 50000
    
    for (acct_id, curr, acc_type), account in portfolio_alice_usd.cash_accounts.items():
        account.balance = 30000
        account.start_balance = 30000
    
    for (acct_id, curr, acc_type), account in portfolio_bob_eur.cash_accounts.items():
        account.balance = 75000
        account.start_balance = 75000
    
    # Create transaction manager
    tm = TransactionManager()
    
    # Transaction sequence: Alice EUR portfolio (stocks + bonds)
    transactions = []
    
    # Sept 2025: Alice starts investing in stocks
    tx1 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 9, 5),
        portfolio_id=portfolio_alice_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=stock_siemens.instrument_id,
        amount=100,
        price=145.0
    )
    transactions.append(('Alice EUR', 'BUY Siemens 100 @ 145', tx1))
    
    # Oct 2025: First bond purchase (small amount to stay within budget)
    tx2 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 10, 1),
        portfolio_id=portfolio_alice_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=bond_eu_gov.instrument_id,
        amount=10,  # 10 bonds @ 1000 nominal = €10k
        price=102.0  # quoted per 100 (102 = 102% of par)
    )
    transactions.append(('Alice EUR', 'BUY EU Bond 10 @ 102', tx2))
    
    # Nov 2025: More bond investment
    tx3 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 11, 10),
        portfolio_id=portfolio_alice_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=bond_corporate.instrument_id,
        amount=8,  # 8 bonds @ 1000 nominal = €8k
        price=101.5  # quoted per 100 (101.5 = 101.5% of par)
    )
    transactions.append(('Alice EUR', 'BUY Corporate Bond 8 @ 101.5', tx3))
    
    # Dec 2025: Increase stock position
    tx4 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 12, 5),
        portfolio_id=portfolio_alice_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=stock_siemens.instrument_id,
        amount=50,
        price=151.0
    )
    transactions.append(('Alice EUR', 'BUY Siemens 50 @ 151', tx4))
    
    # Alice USD portfolio: US stocks and bonds
    tx5 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 9, 10),
        portfolio_id=portfolio_alice_usd.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_usd,
        product_collection=pc,
        currency_prices=cp,
        product_id=stock_apple.instrument_id,
        amount=30,
        price=210.0
    )
    transactions.append(('Alice USD', 'BUY Apple 30 @ 210', tx5))
    
    tx6 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 10, 5),
        portfolio_id=portfolio_alice_usd.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_usd,
        product_collection=pc,
        currency_prices=cp,
        product_id=stock_microsoft.instrument_id,
        amount=15,
        price=385.0
    )
    transactions.append(('Alice USD', 'BUY Microsoft 15 @ 385', tx6))
    
    tx7 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 11, 1),
        portfolio_id=portfolio_alice_usd.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_alice_usd,
        product_collection=pc,
        currency_prices=cp,
        product_id=bond_us.instrument_id,
        amount=2,  # 2 bonds @ 1000 nominal = $2k
        price=101.0  # quoted per 100 (101 = 101% of par)
    )
    transactions.append(('Alice USD', 'BUY US Bond 2 @ 101', tx7))
    
    # Bob EUR portfolio: Conservative (mostly bonds)
    tx10 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 9, 15),
        portfolio_id=portfolio_bob_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_bob_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=bond_eu_gov.instrument_id,
        amount=30,  # 30 bonds @ 1000 nominal = €30k
        price=102.0  # quoted per 100 (102 = 102% of par)
    )
    transactions.append(('Bob EUR', 'BUY EU Bond 30 @ 102', tx10))
    
    tx11 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 10, 10),
        portfolio_id=portfolio_bob_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_bob_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=stock_siemens.instrument_id,
        amount=200,
        price=147.0
    )
    transactions.append(('Bob EUR', 'BUY Siemens 200 @ 147', tx11))
    
    tx12 = tm.create_and_execute_transaction(
        transaction_date=date(2025, 11, 15),
        portfolio_id=portfolio_bob_eur.portfolio_id,
        template=TransactionTemplate.BUY,
        portfolio=portfolio_bob_eur,
        product_collection=pc,
        currency_prices=cp,
        product_id=bond_corporate.instrument_id,
        amount=20,  # 20 bonds @ 1000 nominal = €20k
        price=101.5  # quoted per 100 (101.5 = 101.5% of par)
    )
    transactions.append(('Bob EUR', 'BUY Corporate Bond 20 @ 101.5', tx12))
    
    dataset['transactions'] = transactions
    
    return dataset


if __name__ == "__main__":
    dataset = create_realistic_dataset()
    print(f"Created dataset with:")
    print(f"  - {len(dataset['clients'])} clients")
    print(f"  - {len(dataset['portfolios'])} portfolios")
    print(f"  - {len(dataset['products'])} products")
    print(f"  - {len(dataset['transactions'])} transactions")
