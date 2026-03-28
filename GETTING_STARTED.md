# OpenPortfolio – Getting Started

Deze gids helpt je om snel aan de slag te gaan met OpenPortfolio en de grafische interfaces.

## Snel starten

1. **Installeer afhankelijkheden:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Test de installatie:**
    ```bash
    ./run_tests.sh
    ```

3. **Start de desktop GUI:**
    ```bash
    PYTHONPATH=src .venv/bin/python3 -m open_portfolio.gui
    ```

4. **Start de webinterface:**
    ```bash
    PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
    ```

## GUI Gebruik

**Desktop GUI (Tkinter):**
- Portefeuilles beheren, holdings bekijken, transacties uitvoeren.
- Tabblad "Transactions": selecteer portefeuille, type, product, bedrag, prijs en klik op Execute.
- Tabblad "Overview": toont kas- en effectenposities.

**Web UI (Flask):**
- Overzicht van portefeuilles, transacties en posities via de browser.

## Demo modus

Start met voorbeelddata:
```bash
PYTHONPATH=src .venv/bin/python3 -m open_portfolio.gui --demo
```
Of voor de webinterface:
```bash
PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
```

Demo data bevat o.a. een USD aandeel, EUR obligatie en actuele valutakoersen.

## Notebook & script

Zie `src/portfolio_sim.ipynb` (interactief) en `src/portfolio_sim.py` (script) voor een hands-on demo van de kernfunctionaliteit.

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

## Automatic Deploy (SSH Host, No Docker)

This project now includes a full CI/CD baseline for SSH-based hosting.

### 1. Required GitHub Secrets

Set these repository secrets before enabling deploy:

- `SSH_HOST`
- `SSH_PORT`
- `SSH_USER`
- `SSH_PRIVATE_KEY`
- `APP_DIR` (example: `/srv/open-portfolio`)

### 2. Server Bootstrap

Run once on your server:

```bash
cd /path/to/open_portfolio
chmod +x scripts/bootstrap_server.sh scripts/deploy.sh
./scripts/bootstrap_server.sh /srv/open-portfolio
```

Then copy and edit templates:

- `deploy/systemd/openportfolio.service` -> `/etc/systemd/system/openportfolio.service`
- `deploy/nginx/openportfolio.conf` -> `/etc/nginx/sites-available/openportfolio.conf`

Or generate host-specific files automatically:

```bash
./scripts/configure_deploy_files.sh <app_user> <app_dir> <server_name> <output_dir>
```

Example:

```bash
./scripts/configure_deploy_files.sh deploy /srv/open-portfolio portfolio.example.com /tmp/openportfolio-deploy
```

Generated files:

- `/tmp/openportfolio-deploy/systemd/openportfolio.service`
- `/tmp/openportfolio-deploy/nginx/openportfolio.conf`

Replace placeholders in `openportfolio.service`:

- `__APP_USER__`
- `__APP_DIR__`

Enable services:

```bash
sudo ln -sf /etc/nginx/sites-available/openportfolio.conf /etc/nginx/sites-enabled/openportfolio.conf
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable openportfolio
sudo systemctl restart openportfolio
sudo systemctl restart nginx
```

### 3. CI/CD Workflow

The workflow is defined in `.github/workflows/deploy.yml` and runs:

1. Test stage (`pytest`)
2. Deploy stage (rsync + remote `scripts/deploy.sh`) on pushes to `main`

### 3b. Shared Hosting CI/CD (No systemd/nginx)

For shared hosting environments (for example `htdocs` deployments), use:

- `.github/workflows/deploy-shared-hosting.yml`
- `scripts/deploy_shared_host.sh`

Required secrets:

- `SSH_HOST`
- `SSH_PORT` (must be your real SSH port; often `22`, not FTP port `21`)
- `SSH_USER`
- `SSH_PRIVATE_KEY`
- `APP_DIR` (example: `/home/<user>/htdocs/<domain>`)
- `RESTART_TOUCH_FILE` (example: `/home/<user>/htdocs/<domain>/tmp/restart.txt`)

This shared-hosting deploy path does:

1. Run tests in GitHub Actions
2. Upload code via `rsync`
3. Create/update `.venv` and install requirements remotely
4. Touch `restart.txt` for Passenger-style app restarts

### 4. Health Check

Use:

```bash
curl -fsS http://127.0.0.1:5000/healthz
```

The endpoint returns HTTP 200 when the app is healthy.

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
