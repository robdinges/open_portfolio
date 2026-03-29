# OpenPortfolio – Getting Started

Deze gids helpt je om snel aan de slag te gaan met OpenPortfolio.

## Snel starten

1. **Installeer afhankelijkheden:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test de installatie:**
   ```bash
   ./run_tests.sh
   ```

3. **Start de webinterface:**
   ```bash
   PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
   ```

   De server luistert standaard op `http://127.0.0.1:5000/`.

## Webinterface

### Navigatie

Na het starten van de server zie je een dashboard met:

- Client- en portefeuilleselectie
- Navigatiebalk naar alle schermen

### Beschikbare pagina's

| Pagina | URL | Functie |
|---|---|---|
| Dashboard | `/` | Client/portfolio-selectie, samenvattende statistieken |
| Holdings | `/holdings` | Effecten- en kasposities per portefeuille |
| Transacties | `/transactions` | Transactieoverzicht, gesorteerd op datum |
| Orderinvoer | `/transactions/new` | Transactieformulier met draft-workflow |
| Rekeningen | `/accounts` | Kasrekeningenoverzicht |
| Instrumenten | `/instruments` | Instrumentenlijst met add/edit |
| Order-drafts | `/order-drafts` | Conceptordermonitoring en opschoning |

### Orderinvoer

1. Navigeer naar `/transactions/new`
2. Selecteer client en portefeuille (of navigeer vanuit holdings)
3. Zoek en selecteer een instrument via de instrumentzoeker
4. Kies transactiesoort (BUY/SELL) en ordertype (MARKET/LIMIT)
5. Voer hoeveelheid en eventueel limietprijs in
6. Bekijk de preview: geschatte kosten, opgelopen rente, totaalbedrag
7. Kies een actie:
   - **Bewaren:** sla op als conceptorder (DRAFT)
   - **Bevestigen:** valideer de order (VALIDATED)
   - **Routeren:** dien de order definitief in (SUBMITTED)
   - **Annuleren:** keer terug naar het vorige scherm

### Instrumentbeheer

1. Navigeer naar `/instruments`
2. Klik op **Nieuw instrument** om een aandeel of obligatie toe te voegen
3. Klik op een bestaand instrument om het te bewerken
4. Wijzigingen worden opgeslagen in de SQLite-database

### Demo data

De webapplicatie laadt automatisch een realistische demo-dataset met:

- 2 clients, 3 portefeuilles
- 27 producten (5 aandelen, 22 obligaties)
- 10 voorbeeldtransacties
- Prijshistorie en FX-koersen

## Notebook & script

Zie `src/portfolio_sim.ipynb` (interactief) en `src/portfolio_sim.py`
(script) voor een hands-on demo van de kernfunctionaliteit.

## Projectstructuur

```
open_portfolio/
├── src/
│   └── open_portfolio/
│       ├── __init__.py
│       ├── accounts.py          # Portfolio, CashAccount, SecuritiesAccount
│       ├── analytics.py         # PortfolioAnalytics
│       ├── clients.py           # Client model
│       ├── database.py          # SQLite persistence
│       ├── enums.py             # Enumeraties (TransactionTemplate, etc.)
│       ├── order_entry.py       # OrderDraft, repositories
│       ├── prices.py            # Currency en product pricing
│       ├── product_collection.py # Product registry
│       ├── products.py          # Stock, Bond, Product
│       ├── reporting.py         # PortfolioReporter
│       ├── sample_data.py       # Dataset loader vanuit data/*.json
│       ├── transactions.py      # Transactie-executie en templates
│       ├── utils.py             # TimeTravel helper
│       ├── web_app.py           # Flask webapplicatie
│       ├── wsgi.py              # WSGI entry point
│       └── templates/
│           ├── base.html
│           ├── home.html
│           ├── holdings.html
│           ├── transactions.html
│           ├── transaction_form.html
│           ├── accounts.html
│           ├── clients.html
│           ├── portfolios.html
│           ├── instruments.html
│           ├── instrument_form.html
│           └── order_drafts.html
├── data/
│   ├── clients.json
│   ├── portfolios.json
│   ├── products.json
│   ├── cash_accounts.json
│   ├── prices.json
│   ├── currency_prices.json
│   └── transactions.json
├── tests/
│   ├── test_database.py         # Database-persistentie
│   ├── test_gui_scenario.py     # End-to-end GUI-scenario's
│   ├── test_reporting.py        # Dataset en rapportage
│   ├── test_transactions.py     # Transactie-executie
│   └── test_web_app.py          # Webinterface (30 tests)
└── deploy/
    ├── nginx/openportfolio.conf
    └── systemd/openportfolio.service
```

## Testen

Voer de volledige testsuite uit:

```bash
./run_tests.sh
```

Of direct:

```bash
PYTHONPATH=src .venv/bin/python3 -m pytest tests/ -v
```

Huidige testdekking: **49 tests** verdeeld over:

- **test_database.py** (6 tests): client/portfolio-persistentie,
  order-draft lifecycle, instrumentopslag, thread-safety
- **test_gui_scenario.py** (2 tests): end-to-end menupagina's en
  transactieworkflow
- **test_reporting.py** (5 tests): datasetvalidatie, rapportage
  (summary, holdings, transacties, export)
- **test_transactions.py** (6 tests): BUY/SELL, obligatie-transacties,
  opgelopen rente, saldo-checks
- **test_web_app.py** (30 tests): orderinvoer, instrumentbeheer,
  draft-workflow, validaties, UI-gedrag

## API-overzicht

### Programmatisch een transactie uitvoeren

```python
from open_portfolio.sample_data import create_realistic_dataset
from open_portfolio.enums import TransactionTemplate
from datetime import date

ds = create_realistic_dataset()
portfolio = ds['portfolios'][0]
products = ds['products']
prices = ds['prices']

from open_portfolio.transactions import TransactionManager
tm = TransactionManager()
tx = tm.create_and_execute_transaction(
    transaction_date=date.today(),
    portfolio_id=portfolio.portfolio_id,
    template=TransactionTemplate.BUY,
    portfolio=portfolio,
    product_collection=products,
    currency_prices=prices,
    product_id=5,
    amount=10,
    price=150.00,
)
```

### Database-persistentie

```python
from open_portfolio.database import Database

db = Database("demo.sqlite")
for c in ds['clients']:
    db.add_client(c)
for p in ds['portfolios']:
    db.add_portfolio(p)
db.close()
```

## Troubleshooting

- Bij `ModuleNotFoundError` voor `open_portfolio`: stel
  `PYTHONPATH=src` in.
- De venv-Python is `.venv/bin/python`.
- Gebruik `./run_tests.sh` voor een consistente testomgeving.
