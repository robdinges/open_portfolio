# Project Guidelines

## Code Style
- Follow existing Python style and keep modules small and focused under src/open_portfolio.
- Prefer explicit enums and domain objects already used in the codebase (for example TransactionTemplate, PaymentFrequency, AccountType).
- Keep web route handlers in src/open_portfolio/web_app.py thin: move reusable logic to domain modules when behavior grows.
- For UI behavior and formatting requirements, follow .github/instructions.md.

## Architecture
- Core domain lives in src/open_portfolio:
- accounts.py: Portfolio, cash/securities accounts, holdings valuation.
- products.py and product_collection.py: instruments and registry.
- transactions.py: transaction templates, movements, execution flow.
- prices.py: FX and product pricing.
- sample_data.py: dataset loader from data/*.json.
- web_app.py: Flask UI and form flow.
- reporting.py: console/markdown reporting.
- database.py: lightweight SQLite persistence.
- Data fixtures are in data/*.json and are used by create_realistic_dataset().

## Build and Test
- Use the project virtual environment Python: .venv/bin/python.
- Set import path when running modules/tests: PYTHONPATH=src.
- Install dependencies:
  - pip install -r requirements.txt
- Canonical test command:
  - ./run_tests.sh
- Direct test command equivalent:
  - PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
- Run web app locally:
  - PYTHONPATH=src .venv/bin/python -m open_portfolio.web_app

## Conventions
- Prefer updating tests when behavior/data fixtures change.
- Keep data model keys in data/*.json stable unless the loader and tests are updated together.
- When adding product fields, ensure stock and bond records remain backward-compatible with sample_data.py expectations.
- Avoid hardcoding client/portfolio assumptions in Flask routes; preserve selected context via query params.
- If a command fails with ModuleNotFoundError for open_portfolio, rerun with PYTHONPATH=src.

## Reference Docs
- Setup and runbook: GETTING_STARTED.md
- High-level project overview: README.md
- Feature and model overview: FEATURES.md
- Dataset/reporting details: DATASET_AND_REPORTING.md
- Product and bond workflow requirements: REQUIREMENTS.md
- Order-entry specificatie: ORDER_ENTRY.md
- Planned work and priorities: BACKLOG.md
- UI and presentation specifics: .github/instructions.md
