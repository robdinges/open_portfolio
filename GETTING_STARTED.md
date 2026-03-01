# OpenPortfolio – Getting Started Guide

This guide explains how to set up, run, and use the OpenPortfolio library and its graphical interfaces.

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation:**
    ```bash
    cd /Users/robvandererve/Documents/python_projects/OpenPortfolio
    PYTHONPATH=src .venv/bin/python3 -m pytest tests/ -v
    ```
    The suite currently contains 16 tests and they should all pass.

---

## Running the Desktop GUI

The desktop GUI is a lightweight Tkinter application for managing portfolios, viewing holdings, and executing transactions.

### Basic Usage

```bash
cd /Users/robvandererve/Documents/python_projects/OpenPortfolio
PYTHONPATH=src .venv/bin/python3 -m open_portfolio.gui
```

This launches the interactive GUI. Use the **Transactions** tab to:
- Select a portfolio
- Choose a transaction type (BUY, SELL, DEPOSIT, DIVIDEND)
- Pick a product from the dropdown
- Enter amount and price
- Click **Execute** to process the transaction

The **Overview** tab shows:
- Cash account balances for each portfolio
- Current security holdings

### Demo Mode

To start with sample products and currency prices:

```bash
cd /Users/robvandererve/Documents/python_projects/OpenPortfolio
PYTHONPATH=src .venv/bin/python3 -m open_portfolio.gui --demo
```

Demo data includes:
- **Stock**: Demo USD Stock (ID 1001)
- **Bond**: Demo EUR Bond (ID 1002)
- **Currency rates**: USD/EUR conversion at 1.10

### Headless Mode (for Testing)

To verify the GUI initializes without displaying it:

```bash
PYTHONPATH=src .venv/bin/python3 -m open_portfolio.gui --headless --demo
```

This creates the application, populates demo data, and exits cleanly—useful for automated testing or CI/CD pipelines.

---

## Running the Web GUI

The web GUI is a Flask-based application accessible via a local web browser.

### Start the Web Server

```bash
cd /Users/robvandererve/Documents/python_projects/OpenPortfolio
PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
```

The server listens on `http://127.0.0.1:5000/` by default.

### Access the Web Interface

1. Open your browser to **http://127.0.0.1:5000/**
2. You'll see:
   - A portfolio overview with demo data and holdings
   - A link to the **New Transaction** form
  
    The pages use [Bootstrap](https://getbootstrap.com/) from a CDN for simple responsive styling.

### Creating Transactions via Web UI

1. Navigate to `/transaction/new`
2. Fill in the form:
   - **Portfolio ID**: Select from available portfolios
   - **Transaction Type**: Choose BUY, SELL, DEPOSIT, or DIVIDEND
   - **Product ID**: Select from available products (includes demo products by default)
   - **Amount**: Enter the quantity or cash amount
   - **Price**: Enter the unit price
3. Click **Submit**
4. Feedback message confirms success or displays errors

### Demo Data

The web app auto-populates with the same realistic dataset used by
`create_realistic_dataset()`: two clients, three portfolios, eight
products and a handful of example transactions.  This means when the
server starts you can immediately browse the portfolios, execute new
transactions, and after each trade you'll see a summary panel showing
the five most recent transactions, current positions and cash balances.

---

## Project Structure

```
OpenPortfolio/
├── src/
│   └── open_portfolio/              # Main package
│       ├── __init__.py              # Public API exports
│       ├── accounts.py              # Portfolio, CashAccount, SecuritiesAccount
│       ├── clients.py               # Client management
│       ├── enums.py                 # Enumerations (TransactionTemplate, etc.)
│       ├── prices.py                # Currency and product pricing
│       ├── products.py              # Stock, Bond, and Product base class
│       ├── product_collection.py    # Product registry
│       ├── transactions.py          # Transaction creation, execution, templates
│       ├── utils.py                 # TimeTravel helper
│       ├── gui.py                   # Tkinter desktop application
│       └── web_app.py               # Flask web application
├── tests/
│   ├── test_open_portfolio_lib.py   # Core library tests
│   ├── test_transactions.py         # Transaction tests
│   └── test_pytest_sample.py        # Sample test
└── README.md                        # Original project documentation
```

---

## Testing

Run the full test suite (note the `PYTHONPATH` so the package is
discoverable):

```bash
PYTHONPATH=src .venv/bin/python3 -m pytest tests/ -v
```

Current test coverage:

- **16 passing tests** covering:
    - Transaction creation and execution (BUY, SELL, DEPOSIT, DIVIDEND)
    - Bond accrued interest calculation
    - Cash account balance updates and multi-currency handling
    - Insufficient funds detection
    - TimeTravel date manipulation
    - Multi-buy transaction sequences
    - Reporting output (summary, holdings, history, text export)
    - Web UI behaviour (form submission, transaction summary display)

---

## API Overview

### Creating a Portfolio Programmatically

```python
from open_portfolio import Client, TransactionManager
from open_portfolio.products import Stock, Bond
from open_portfolio.enums import TransactionTemplate
from datetime import date

# Create a client and portfolio
client = Client(client_id=1, name="My Portfolio")
portfolio = client.add_portfolio(portfolio_id=1)

# Add a cash account with starting balance
cash_account = portfolio.add_cash_account(
    account_id=1,
    currency="USD",
    start_balance=10000.0
)

# Create a stock and execute a BUY transaction
stock = Stock(
    product_id=1,
    description="Apple Inc.",
    minimum_purchase_value=1,
    smallest_trading_unit=1,
    issue_currency="USD"
)

tm = TransactionManager()
tx = tm.create_and_execute_transaction(
    transaction_date=date.today(),
    portfolio_id=portfolio.portfolio_id,
    template=TransactionTemplate.BUY,
    portfolio=portfolio,
    product_collection=ProductCollection(),  # Add your products here
    currency_prices=CurrencyPrices(),
    product_id=stock.instrument_id,
    amount=100,
    price=150.00
)
```

### Listing Holdings and Transactions

```python
# View all holdings
portfolio.list_holdings(valuation_date=date.today())

# View all transactions
txs = portfolio.list_all_transactions()
for tx in txs:
    print(tx)

# View accounts and balances
portfolio.list_accounts()
```

### Simple Database Persistence

If you'd like to persist the objects created during tests or demos, a very
lightweight SQLite wrapper is provided in ``open_portfolio.database``.  It
maintains two tables (clients and portfolios) and can be pointed at an on-disk
file or run entirely in memory.

```python
from open_portfolio.database import Database

# file-backed database (use ":memory:" for ephemeral storage)
db = Database("demo.sqlite")

# make some objects and save them
client = Client(1, "Alice")
portfolio = client.add_portfolio(1)
db.add_client(client)
db.add_portfolio(portfolio)

print(db.get_clients())
print(db.get_portfolios())

db.close()
```

The new test file ``tests/test_database.py`` demonstrates basic round-tripping;
run it with ``pytest`` along with the rest of the suite.

---

## Troubleshooting

### GUI Does Not Display (Headless Environment)

If you're running on a server without a display:
1. Use `--headless` mode for testing: `python3 -m open_portfolio.gui --headless`
2. Or use the web GUI instead: `python3 -m open_portfolio.web_app`

### "No module named 'open_portfolio'"

Ensure you set `PYTHONPATH=src` before running:
```bash
PYTHONPATH=src python3 -m open_portfolio.gui
```

### Flask Port Already in Use

If port 5000 is busy, modify `web_app.py` to use a different port:
```python
if __name__ == "__main__":
    app = make_app()
    app.run(host="127.0.0.1", port=5001, debug=False)  # Change port here
```

### Tests Fail with Import Errors

Make sure to use the virtualenv Python:
```bash
.venv/bin/python3 -m pytest tests/
```

---

## Feature Highlights

- ✅ **Modular Architecture**: Separate modules for accounts, transactions, products, pricing, database, GUI and reporting
- ✅ **Rich Data Model**: Clients own portfolios; portfolios contain cash and securities accounts; securities reference products; transactions record cash and security movements
- ✅ **Multiple UI Options**: Desktop (Tkinter) and web (Flask) interfaces, both with demo mode and interactive transaction forms
- ✅ **Transaction Templates**: Pre-defined BUY, SELL, DEPOSIT, and DIVIDEND templates for common operations
- ✅ **Multi-Currency Support**: EUR/USD pricing with exchange rates and cash account handling
- ✅ **Bond Support**: Fixed-income instruments with maturity dates, interest rates, and accrued interest calculations
- ✅ **Realistic Dataset Generator**: `create_realistic_dataset()` builds multi-client, multi-portfolio test data with price history and transactions
- ✅ **Comprehensive Reporting**: Detailed console reports including portfolio summary, holdings, transaction history, and cash position; exportable as plain text
- ✅ **Web Transaction Summary**: After executing a trade via the web UI, users immediately see the last 5 transactions, current positions, and cash balances
- ✅ **Lightweight SQLite Persistence**: Simple database wrapper with client/portfolio tables and helper tests
- ✅ **Extensive Testing**: 16 unit tests cover core logic, reporting, and web UI behaviour
- ✅ **Flexible Demo Modes**: CLI flags for headless or demo operation; easy script reuse for automated workflows


---

## Next Steps

1. **Customize demo data**: Edit `gui.py` and `web_app.py` to add your own products and accounts
2. **Extend transaction types**: Add new transaction templates in `enums.py` and `transactions.py`
3. **Integrate with a database**: Replace in-memory storage with a persistent database backend
4. **Deploy the web app**: Use a production WSGI server like Gunicorn or uWSGI

---

## Support

For issues or questions, refer to:
- `README.md` – Original project documentation
- `src/open_portfolio/*.py` – Module docstrings and code comments
- `tests/` – Working examples of API usage

Happy investing! 📈
