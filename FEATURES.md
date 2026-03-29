# OpenPortfolio Features & Data Model

Dit document geeft een overzicht van de belangrijkste mogelijkheden en
de datastructuur van OpenPortfolio.

## Features

- **Modulair & uitbreidbaar:** Accounts, clients, producten, transacties,
  pricing, rapportage, analytics, database.
- **Webinterface (Flask):** Dashboard, holdings, transacties, orderinvoer,
  instrumentbeheer, order-draft monitoring, rekeningenoverzicht.
- **Orderinvoer:** Volledig transactieformulier met draft/validate/submit-
  workflow, BUY/SELL met MARKET/LIMIT, instrumentzoeker met positie-
  indicator, kostencalculatie, opgelopen rente, FX-conversie.
- **Instrumentbeheer:** Aandelen en obligaties toevoegen en bewerken via
  web-UI; opties en fondsen ondersteund als producttype; persistentie in
  SQLite; actief/inactief-filtering.
- **Order-draft lifecycle:** Conceptorders met status
  (DRAFT/VALIDATED/REJECTED/SUBMITTED), SQLite-persistentie,
  retentiebeleid en monitoringpagina.
- **Demo data generator:** Automatisch realistische datasets voor testen en
  demo's (27 producten, 3 portefeuilles, 10 transacties).
- **Transactietemplates:** BUY, SELL, DEPOSIT, DIVIDEND (met validatie).
- **Multi-valuta:** EUR, USD, GBP, CHF, NOK met automatische FX-conversie.
- **Producten:** Aandelen, obligaties, opties en fondsen (incl. rente-opbouw
  en aflossing voor obligaties).
- **Rapportage:** Overzicht, holdings, transacties, kaspositie
  (console, tekst en markdown).
- **Database:** SQLite-persistentie voor clients, portefeuilles, conceptorders
  en instrumenten met thread-safe wrapper.
- **Testen:** Uitgebreide pytest-suite (49 tests).

## Objectmodel

```
Client
  └─ portfolios: List[Portfolio]
         ├─ cash_accounts: Dict[(id,currency,type), CashAccount]
         │      ├─ balance, start_balance, transactions
         │      └─ get_balance(valuation_date)
         ├─ securities_account: SecuritiesAccount
         │      ├─ holdings: List[{product, amount}]
         │      └─ get_holding_values(valuation_date)
         ├─ list_all_transactions() -> list of tx dicts
         └─ calculate_holding_value(valuation_date)

CashAccount
  ├─ cash_account_id, currency, account_type
  ├─ start_balance, balance, exchange_rate
  ├─ transactions: List[Transaction]
  └─ methods: add_transaction(), get_balance(date)

SecuritiesAccount
  ├─ portfolio_id, currency, start_date
  ├─ holdings: List[{product, amount}]
  └─ get_holding_values(valuation_date)

Product (base)
  ├─ instrument_id, description, type (InstrumentType)
  ├─ issue_currency, isin
  ├─ minimum_purchase_value, smallest_trading_unit
  ├─ prices: List[(date, price)]
  ├─ transactions: List[SecurityMovement]
  └─ methods: add_price(), get_price(date), is_bond(), is_active()

Stock (Product)
  └─ type = InstrumentType.STOCK

Bond (Product)
  ├─ start_date, maturity_date
  ├─ interest_rate, interest_payment_frequency
  └─ calculate_accrued_interest(nominal, date, interest_type)

ProductCollection
  ├─ registry van producten op instrument_id
  └─ add_product(), get_product(), iterable

TransactionManager
  ├─ create_transaction() met templates
  ├─ execute_transaction(tx, portfolio, product_collection)
  └─ create_and_execute_transaction() (combined)

Transaction
  ├─ transaction_number, transaction_date, portfolio_id
  ├─ cash_movements: List[CashMovement]
  ├─ security_movements: List[SecurityMovement]
  └─ to_dict(), validate()

OrderDraft
  ├─ draft_id, status (OrderStatus enum)
  ├─ payload: Dict, validity_date
  ├─ errors, warnings
  └─ created_at, updated_at

OrderStatus (Enum)
  └─ DRAFT, VALIDATED, REJECTED, SUBMITTED

InMemoryOrderRepository / DatabaseOrderRepository
  └─ upsert_draft(), get_draft(), set_status()

CurrencyPrices
  ├─ maps (currency, date) -> price
  └─ FX-conversie en waardering

PortfolioReporter
  ├─ print_summary(), print_detailed_holdings()
  ├─ print_transaction_history(), print_cash_position()
  ├─ print_all_reports()
  └─ to_text(), to_markdown()

PortfolioAnalytics
  └─ get_holdings_progress(product_id) -> historisch verloop

Database (SQLite)
  ├─ tabellen: client, portfolio, order_draft, instrument
  ├─ add_client(), add_portfolio(), get_clients(), get_portfolios()
  ├─ upsert_order_draft(), get_order_draft(), list_order_drafts()
  ├─ purge_stale_order_drafts(), get_order_draft_status_counts()
  └─ upsert_instrument(), list_instruments()

Enums
  ├─ TransactionTemplate: BUY, SELL, DIVIDEND, DEPOSIT
  ├─ InstrumentType: STOCK, BOND, FUND, OPTION
  ├─ AccountType: CASH, SAVINGS, OBLIGO, DEPOSIT, SECURITIES
  ├─ PaymentFrequency: MONTH, YEAR, END_DATE
  ├─ InterestType: ACT_ACT, THIRTY_360
  ├─ MovementType: TAX, COSTS, SECURITY_BUY, SECURITY_SELL,
  │     ACCRUED_INTEREST, DEPOSIT, WITHDRAWAL, INTEREST, etc.
  └─ QuotationType: NOMINAL, AMOUNT
```

## Webinterface routes

| Route | Methode | Functie |
|---|---|---|
| `/` | GET | Dashboard met client/portefeuilleselectie |
| `/holdings` | GET | Effecten- en kasposities |
| `/transactions` | GET | Transactieoverzicht |
| `/transactions/new` | GET/POST | Orderinvoerformulier |
| `/accounts` | GET | Kasrekeningenoverzicht |
| `/instruments` | GET/POST | Instrumentenlijst en toevoegen |
| `/instruments/new` | GET/POST | Nieuw instrument aanmaken |
| `/instruments/edit/<id>` | GET/POST | Instrument bewerken |
| `/order-drafts` | GET/POST | Order-draft monitoring en opschoning |
| `/healthz` | GET | Health check endpoint |

## Typical Workflows

1. **Experiment met realistische data**
   ```python
   from open_portfolio.sample_data import create_realistic_dataset
   from open_portfolio.reporting import PortfolioReporter

   ds = create_realistic_dataset()
   reporter = PortfolioReporter(ds['clients'])
   reporter.print_all_reports()
   ```

2. **Webinterface starten**
   ```bash
   PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
   # browse naar http://127.0.0.1:5000
   ```

3. **Transacties inspecteren**
   ```python
   p = ds['clients'][0].portfolios[0]
   print(p.list_all_transactions())
   p.list_holdings()
   ```

4. **Database-persistentie**
   ```python
   from open_portfolio.database import Database

   db = Database('demo.sqlite')
   for c in ds['clients']:
       db.add_client(c)
   for p in ds['portfolios']:
       db.add_portfolio(p)
   ```

## Notes

- Stel altijd `PYTHONPATH=src` in of installeer het package in
  editable mode.
- Tests oefenen het overgrote deel van de functionaliteit; voeg tests
  toe bij het uitbreiden van modules.
- De demo-dataset is bruikbaar in zowel CLI, web als notebook-context.
- Documentatie staat verspreid over docstrings, `GETTING_STARTED.md`,
  `FEATURES.md` en de overige `.md`-bestanden.
