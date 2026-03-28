---
name: pricing-and-valuation
description: 'Implement and troubleshoot pricing and valuation behavior in OpenPortfolio. Use for FX rate retrieval, reverse FX handling, product price timelines, valuation-date logic, latest-price-at-transaction-date behavior, accrued interest behavior, and portfolio/report valuation consistency.'
argument-hint: 'Describe valuation date, currencies, instruments, expected valuation output, and failing tests.'
---

# Pricing And Valuation

## When to Use
- Fix incorrect FX conversion or missing FX fallback behavior.
- Update product/currency pricing retrieval logic.
- Debug valuation discrepancies in holdings, portfolio totals, or reports.
- Adjust accrued interest behavior for bonds.
- Investigate valuation-date edge cases.
- Validate order totals that depend on latest instrument and FX rates on or before transaction date.

## Primary Code Touchpoints
- `src/open_portfolio/prices.py`
- `src/open_portfolio/accounts.py`
- `src/open_portfolio/products.py`
- `src/open_portfolio/reporting.py`
- `tests/test_reporting.py`
- `tests/test_transactions.py`

## Procedure
1. Pin down valuation contract.
- Determine valuation date and target currency.
- Separate price issues from movement/transaction issues.
- For order entry, determine transaction date and exact rate/price lookup rule.

2. Reproduce with smallest path.
- Use focused tests or a minimal dataset path through `create_realistic_dataset()`.
- Confirm whether mismatch starts at FX lookup, product price, or accrued-interest step.

3. Apply minimal domain fix.
- Keep FX retrieval behavior deterministic in `prices.py`.
- Keep valuation aggregation logic in domain modules, not UI routes.
- Ensure latest rate lookup uses `<= date` semantics for both direct and reverse FX paths.

4. Verify report-level consistency.
- Confirm summary, holdings, and transaction outputs align on the same valuation assumptions.

5. Run targeted tests.
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_reporting.py -q`
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_transactions.py -q`

## Validation Checklist
- Direct and reverse FX lookups behave as expected.
- Product price selection uses latest valid price up to valuation date.
- Bond accrued-interest calculations are stable for supported conventions.
- Portfolio totals reconcile with holdings plus cash.
- Reporting output is consistent across sections.
- Transaction-date valuation inputs (price/FX) are consistent with order totals and cost display.

## Pitfalls
- Confusing quote direction in FX pairs.
- Mixing transaction-date and valuation-date semantics.
- Applying formatting-level rounding too early in calculations.
- Fixing display logic while root cause is domain valuation logic.
- Using valuation-date price rules for transaction-date market-order calculations.

## References
- `ORDER_ENTRY.md`
