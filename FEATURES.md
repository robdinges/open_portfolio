# OpenPortfolio Features & Data Model

This document gives a quick reference to the capabilities of the
OpenPortfolio library and an overview of the underlying object model so
that you can pick things up quickly in future sessions.

## High‑Level Features

- **Modular, extensible codebase** with separate packages for each
  concern (accounts, clients, products, transactions, pricing, GUI,
  reporting, database).
- **Multiple user interfaces**:
  - Desktop GUI built with Tkinter (`gui.py`)
  - Web GUI built with Flask (`web_app.py`)
- **Auto‑generated demo data** and a richer realistic dataset
  generator (`sample_data.py`).
- **Transaction templates** covering common operations:
  BUY, SELL, DEPOSIT, DIVIDEND.  Templates simplify input and validation.
- **Multi‑currency support** including cash accounts denominated in EUR
  and USD with exchange rate handling.
- **Products** cover both stocks and bonds; bonds include interest
  accrual and maturity date logic.
- **Reporting module** (`reporting.py`) produces summary, holdings,
  transaction history and cash position reports, either printed to
  console or exported as plain text.
- **Web UI enhancements**: after each transaction the page displays the
  last 5 trades, current positions and cash balances.
- **Database persistence**: lightweight SQLite wrapper (`database.py`) for
  clients and portfolios with simple read/write methods.
- **Comprehensive testing**: 15 pytest cases validate core logic,
  reporting and web UI behaviour.
- **CLI tools & demo modes**: headless GUI, demo web server, and scriptable
  dataset/report generation.

## Object Model Overview

```
Client
  └─ portfolios: List[Portfolio]
         ├─ cash_accounts: Dict[(id,currency,type), CashAccount]
         │      ├─ balance, start_balance, transactions
         │      └─ get_balance(valuation_date)
         ├─ securities_account: SecuritiesAccount
         │      ├─ holdings: List[{product,amount}]
         │      └─ get_holding_values(valuation_date)
         ├─ list_all_transactions() -> serializable list of tx dicts
         └─ calculate_holding_value(valuation_date)

CashAccount
  ├─ cash_account_id, currency, account_type
  ├─ start_balance, balance, exchange_rate
  ├─ transactions: List[Transaction]
  └─ methods to add transactions and compute balance

SecuritiesAccount
  ├─ portfolio_id, currency, start_date
  ├─ holdings: each contains product and amount
  └─ calculate values for holdings as of a date

Product (base)
  ├─ instrument_id, description, issue_currency
  ├─ minimum_purchase_value, smallest_trading_unit
  ├─ transactions: list of security movements
  ├─ get_price(date) via CurrencyPrices
  └─ subclasses: Stock, Bond

Bond (Product)
  ├─ start_date, maturity_date
  ├─ interest_rate, payment_frequency
  └─ calculate_accrued_interest(date)

TransactionManager
  ├─ create transaction objects using templates
  ├─ execute_transaction(tx, portfolio, product_collection)
  └─ simple validation (no negative cash balances)

Transactions & Movements
  ├─ Transaction object contains metadata and lists of
  │  cash_movements and security_movements
  ├─ Movement objects include amount, currency, exchange rate
  └─ Portfolios record transactions in cash accounts

ProductCollection
  ├─ registry of products keyed by instrument_id
  ├─ add_product()/get_product()/iterable access

CurrencyPrices
  ├─ maps (currency, date) -> price
  ├─ used for FX conversion and valuation

Reporting
  ├─ PortfolioReporter(clients)
  ├─ print_summary(), print_detailed_holdings(),
  │  print_transaction_history(), print_cash_position()
  ├─ print_all_reports()
  └─ to_text() for exporting

Database
  ├─ SQLite wrapper with tables for clients and portfolios
  ├─ save_client(), save_portfolio(), get_clients(), get_portfolios()
  └─ Intended for simple persistence/demos

GUI & Web UI
  ├─ `gui.py` (Tkinter) – desktop application with demo & headless flags
  └─ `web_app.py` (Flask) – local web server with transaction form and
     instant portfolio summaries
```

## Typical Workflows

1. **Experiment with realistic data**
   ```python
   from open_portfolio.sample_data import create_realistic_dataset
   ds = create_realistic_dataset()
   clients = ds['clients']
   reporter = PortfolioReporter(clients)
   reporter.print_all_reports()
   ```

2. **Run web interface**
   ```bash
   PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
   # browse to http://127.0.0.1:5000
   ```
   execute trades and watch portfolio summary appear below the form.

3. **Inspect transactions programmatically**
   ```python
   p = clients[0].portfolios[0]
   print(p.list_all_transactions())
   p.list_holdings()
   ```

4. **Persist to database**
   ```python
   from open_portfolio.database import Database
   db = Database('test.db')
   for c in clients:
       db.add_client(c)
   for p in clients[0].portfolios:
       db.add_portfolio(p)
   ```

## Notes for Next Time

- Always set `PYTHONPATH=src` or install package in editable mode.
- Tests exercise most functionality; add more tests when you extend a
  module.
- The demo dataset can be re-used in both CLI, GUI and web contexts.
- Documentation is scattered across docstrings, `GETTING_STARTED.md`,
  and `FEATURES.md` – search for keywords like "PortfolioReporter" or
  "create_realistic_dataset" if you forget the exact API.

---

Keep this file handy; it’s the quickest route to remembering how the
library is put together.
