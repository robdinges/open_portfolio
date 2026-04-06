# REQ-06 — Architectuur en techniek

Datum: 2026-04-06
Bron: `GETTING_STARTED.md`, `web_app.py`, `wsgi.py`, GitHub Actions workflows, deploy-scripts

---

## 1. Modulestructuur

| Regel | Beschrijving | Status |
|---|---|---|
| AT-001 | Codebase leeft onder `src/open_portfolio/`. Imports via `open_portfolio.*`. | [IMPL] |
| AT-002 | Domeinmodules: `accounts.py`, `transactions.py`, `products.py`, `prices.py`, `clients.py`, `enums.py`, `analytics.py`. | [IMPL] |
| AT-003 | Persistentielaag: `database.py` (SQLite). | [IMPL] |
| AT-004 | Web-laag: `web_app.py` (Flask routes, helpers, make_app). | [IMPL] |
| AT-005 | WSGI-entrypoint: `wsgi.py` (module-level `app` voor gunicorn). | [IMPL] |
| AT-006 | Reporting: `reporting.py` (console/markdown/text). | [IMPL] |
| AT-007 | Demodata: `sample_data.py` + `data/*.json`. | [IMPL] |
| AT-008 | Utility: `utils.py` (TimeTravel helper). | [IMPL] |

## 2. App factory pattern

| Regel | Beschrijving | Status |
|---|---|---|
| AT-010 | `make_app(client, product_collection, currency_prices, order_database)` retourneert geconfigureerde Flask-app. | [IMPL] |
| AT-011 | Alle parameters optioneel; zonder argumenten wordt demodata geladen via `create_demo_data()`. | [IMPL] |
| AT-012 | Context processor injecteert 4 template-helpers: `format_currency`, `format_quantity`, `translate_movement_type`, `translate_instrument_type`. | [IMPL] |
| AT-013 | Routes worden binnen `make_app` geregistreerd als closures met toegang tot domeinobjecten. | [IMPL] |
| AT-014 | Testen gebruiken dezelfde `make_app()` met in-memory database. | [IMPL] |

## 3. Opstart-sequentie

| Regel | Beschrijving | Status |
|---|---|---|
| AT-020 | Flask-app wordt aangemaakt via `make_app()`. | [IMPL] |
| AT-021 | Context processor voor template-helpers wordt geregistreerd. | [IMPL] |
| AT-022 | Databaseverbinding wordt geopend (order-DB). | [IMPL] |
| AT-023 | Verlopen conceptorders worden opgeschoond (retentie-check). | [IMPL] |
| AT-024 | Opgeslagen instrumenten worden hersteld uit DB naar ProductCollection. | [IMPL] |
| AT-025 | Routes worden geregistreerd (11 routes). | [IMPL] |
| AT-026 | App is klaar om requests te verwerken. | [IMPL] |

## 4. Flask routes

| Route | Methoden | Doel | Status |
|---|---|---|---|
| `/` | GET | Dashboard (client/portefeuille-selectie) | [IMPL] |
| `/healthz` | GET | Health-check (`{"status": "ok"}`) | [IMPL] |
| `/holdings` | GET | Holdings-overzicht | [IMPL] |
| `/accounts` | GET | Kasrekeningenoverzicht | [IMPL] |
| `/transactions` | GET | Transactie-historie | [IMPL] |
| `/transaction-entry` | GET, POST | Order-invoerformulier | [IMPL] |
| `/instruments` | GET | Instrumentenlijst | [IMPL] |
| `/instruments/new` | GET, POST | Nieuw instrument aanmaken | [IMPL] |
| `/instruments/<id>/edit` | GET, POST | Instrument bewerken | [IMPL] |
| `/order-drafts` | GET, POST | Conceptorders beheren | [IMPL] |
| `/order-drafts/<id>/resume` | GET | Concept hervatten | [IMPL] |

## 5. Configuratie via environment variables

| Variabele | Default | Doel | Status |
|---|---|---|---|
| `OPEN_PORTFOLIO_ENABLE_TX_DATE_EDIT` | `0` | Transactiedatum bewerkbaar in UI | [IMPL] |
| `OPEN_PORTFOLIO_ORDER_DB_PATH` | `open_portfolio_orders.sqlite3` | Pad naar orderdatabase | [IMPL] |
| `OPEN_PORTFOLIO_ORDER_DRAFT_RETENTION_DAYS` | `30` | Retentieperiode voor conceptorders in dagen | [IMPL] |
| `OPEN_PORTFOLIO_PORT` | `5000` | Poort voor development server | [IMPL] |
| `PYTEST_CURRENT_TEST` | (gezet door pytest) | Detectie van testmodus; schakelt in-memory DB in | [IMPL] |

## 6. Database

### 6.1 SQLite

| Regel | Beschrijving | Status |
|---|---|---|
| AT-060 | Enkele SQLite-database voor orders, instrumenten, clients, portefeuilles. | [IMPL] |
| AT-061 | Thread-safe wrapper: verbinding per aanroep. | [IMPL] |
| AT-062 | Tabellen worden autocreated bij eerste gebruik (geen migratie-framework). | [IMPL] |
| AT-063 | Testmodus: `:memory:` database, automatisch gedetecteerd via `PYTEST_CURRENT_TEST`. | [IMPL] |

### 6.2 Migratiebenadering

| Regel | Beschrijving | Status |
|---|---|---|
| AT-065 | Geen formeel migratie-framework (Alembic/Flyway). | [IMPLICIET] |
| AT-066 | Schema-wijzigingen worden handmatig doorgevoerd of via table-recreate. | [IMPLICIET] |
| AT-067 | Bij migratie-noodzaak: overweeg Alembic of versioned schema-scripts. | [GAP] |

## 7. Deployment

### 7.1 CI/CD pipeline

| Regel | Beschrijving | Status |
|---|---|---|
| AT-070 | GitHub Actions workflow: `.github/workflows/deploy.yml`. | [IMPL] |
| AT-071 | Trigger: push op main/master. | [IMPL] |
| AT-072 | Stap 1 — Test: ubuntu-latest, Python 3.11, `pytest`. | [IMPL] |
| AT-073 | Stap 2 — Deploy: SSH-key setup, rsync naar server, remote deploy-script. | [IMPL] |
| AT-074 | Vereiste secrets: `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_PRIVATE_KEY`, `APP_DIR`, `RESTART_TOUCH_FILE`. | [IMPL] |

### 7.2 Shared hosting variant

| Regel | Beschrijving | Status |
|---|---|---|
| AT-080 | Alternatieve workflow: `.github/workflows/deploy-shared-hosting.yml`. | [IMPL] |
| AT-081 | Trigger: workflow_dispatch of push. | [IMPL] |
| AT-082 | Draait `deploy_shared_host.sh` met Passenger-compatibele restart (touch file). | [IMPL] |
| AT-083 | Installeert alleen Flask + gunicorn (niet volledige requirements.txt). | [IMPL] |
| AT-084 | Bootstrap pip van `get-pip.py` als ontbrekend. | [IMPL] |

### 7.3 Serverruntime

| Regel | Beschrijving | Status |
|---|---|---|
| AT-090 | Productieserver: gunicorn met 3 workers, gebonden aan 127.0.0.1:5000. | [IMPL] |
| AT-091 | systemd service (`deploy/systemd/openportfolio.service`): auto-restart, logging. | [IMPL] |
| AT-092 | `PYTHONPATH=src` vereist als omgevingsvariabele. | [IMPL] |
| AT-093 | DB-pad configureerbaar via `OPEN_PORTFOLIO_ORDER_DB_PATH`. | [IMPL] |
| AT-094 | Health-check endpoint `/healthz` beschikbaar voor nginx/systemd probes. | [IMPL] |

## 8. Testing

| Regel | Beschrijving | Status |
|---|---|---|
| AT-100 | Testframework: pytest. | [IMPL] |
| AT-101 | Canonical command: `./run_tests.sh` (wrapper met `PYTHONPATH=src`). | [IMPL] |
| AT-102 | Direct equivalent: `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`. | [IMPL] |
| AT-103 | 5 testbestanden, 49+ tests. | [IMPL] |
| AT-104 | `test_database.py`: client/portfolio persistentie, order-draft lifecycle, thread-safety. | [IMPL] |
| AT-105 | `test_gui_scenario.py`: end-to-end menu & workflow. | [IMPL] |
| AT-106 | `test_reporting.py`: dataset validatie, reporting output. | [IMPL] |
| AT-107 | `test_transactions.py`: BUY/SELL, obligations, opgelopen rente, saldo-checks. | [IMPL] |
| AT-108 | `test_web_app.py`: order-entry, instrumentbeheer, draft workflow, UI-validaties. | [IMPL] |
| AT-109 | CI draait testen automatisch in GitHub Actions vóór deployment. | [IMPL] |

## 9. Python-versies en dependencies

### 9.1 Python-versies

| Omgeving | Versie | Status |
|---|---|---|
| Lokale ontwikkeling | Python 3.14.3 (.venv) | [IMPL] |
| CI (GitHub Actions) | Python 3.11 | [IMPL] |
| Server (productie) | Python 3.11.2 | [IMPL] |

### 9.2 Runtime-dependencies

| Package | Doel | Status |
|---|---|---|
| Flask | Webframework | [IMPL] |
| gunicorn | WSGI-server (productie) | [IMPL] |
| pytest | Testrunner (alleen dev/CI) | [IMPL] |

### 9.3 Opmerking

| Regel | Beschrijving | Status |
|---|---|---|
| AT-120 | `requirements.txt` bevat veel extra dev/data-science pakketten (Jupyter, Pandas, LangChain, etc.) die niet nodig zijn voor runtime. | [IMPLICIET] |
| AT-121 | Overweeg minimale `requirements-prod.txt` voor deployment. | [GAP] |

## 10. Beveiliging en middleware

| Regel | Beschrijving | Status |
|---|---|---|
| AT-130 | Geen authenticatie of autorisatie geïmplementeerd. | [IMPLICIET] |
| AT-131 | Geen CORS-configuratie. | [IMPLICIET] |
| AT-132 | Geen request/response logging middleware. | [IMPLICIET] |
| AT-133 | Geen custom error-handlers (`@app.errorhandler`); Flask-defaults. | [IMPLICIET] |
| AT-134 | Geen CSRF-protectie op formulieren. | [GAP] |
| AT-135 | Geen rate-limiting. | [IMPLICIET] |

## 11. Lokale ontwikkeling

| Regel | Beschrijving | Status |
|---|---|---|
| AT-140 | Entrypoint: `python -m open_portfolio.web_app`. | [IMPL] |
| AT-141 | Doodt eventueel stale processen op de poort (via `lsof`). | [IMPL] |
| AT-142 | Flask debug-modus met `use_reloader=False`. | [IMPL] |
| AT-143 | Demodata wordt automatisch geladen bij start. | [IMPL] |
