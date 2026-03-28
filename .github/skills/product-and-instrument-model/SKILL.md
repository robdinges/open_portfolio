---
name: product-and-instrument-model
description: 'Extend and maintain product and instrument schema in OpenPortfolio. Use for products.json changes, stock/bond/option/fund field compatibility, ISIN and bond metadata mapping, order-entry unit/min-size contracts, loader-safe schema evolution, and model updates across products.py and sample_data.py.'
argument-hint: 'Describe field changes, source format (CSV/JSON), and backward-compatibility constraints.'
---

# Product And Instrument Model

## When to Use
- Add new product fields in `data/products.json`.
- Import or normalize bond metadata (ISIN, coupon, maturity, settlement, broker data).
- Keep stock, bond, option, and fund records consistent when schema evolves.
- Update model parsing in `sample_data.py` after schema changes.
- Fix breakage caused by field naming mismatches.

## Primary Code Touchpoints
- `data/products.json`
- `src/open_portfolio/products.py`
- `src/open_portfolio/sample_data.py`
- `src/open_portfolio/product_collection.py`
- `tests/test_reporting.py`
- `tests/test_transactions.py`

## Procedure
1. Define schema delta explicitly.
- List required fields, optional fields, default behavior, and nullability.
- Separate bond-only fields from common fields.
- Capture order-entry field contracts per instrument type (unit, min order, limit-input semantics).

2. Preserve compatibility contract.
- Keep required keys used by loader stable (`product_id`, `type`, `minimum_purchase_value`, `smallest_trading_unit`, `issue_currency`).
- Ensure old records still parse if new fields are optional.
- Ensure `type` supports UI branching for `stock`, `bond`, `option`, `fund` without ambiguous aliases.

3. Implement loader-safe updates.
- Update `sample_data.py` only as needed for parsing and object creation.
- Avoid introducing schema assumptions that force immediate updates in unrelated fixtures.

4. Normalize imported sources.
- Map source columns to canonical JSON keys.
- Normalize dates (`YYYY-MM-DD`) and rates (decimal where required by model).
- Keep naming consistent (`interest_rate`, `interest_payment_frequency`).
- Keep quantity semantics explicit: bonds nominal, others units unless overridden by product config.

5. Add and run regression checks.
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_reporting.py -q`
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_transactions.py -q`

## Validation Checklist
- All products load through `create_realistic_dataset()` without parsing failures.
- Bond frequency strings map to valid `PaymentFrequency` enum values.
- Added fields do not break existing stock/bond/option/fund records.
- Product counts/assumptions in tests are updated only when required.
- Product schema carries enough metadata to render order fields and validations consistently.

## Pitfalls
- Using new keys without updating loader expectations.
- Mixing percent and decimal formats for rates.
- Date formats that are not ISO-8601.
- Accidental schema drift between `data/products.json` and domain constructors.
- Adding new instrument types without corresponding UI branch rules.

## References
- `ORDER_ENTRY.md`
