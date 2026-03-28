---
name: transaction-engine
description: 'Implement and debug transaction execution logic for BUY, SELL, DEPOSIT, and DIVIDEND. Use for order-entry workflow, market/limit order handling, cash/security movements, settlement currency selection, FX conversion, costs, accrued interest, buying power checks, and insufficient position handling in OpenPortfolio.'
argument-hint: 'Describe transaction type, expected behavior, failing scenario, and touched files.'
---

# Transaction Engine

## When to Use
- Add or change transaction behavior in BUY/SELL/DEPOSIT/DIVIDEND templates.
- Implement or debug order-entry behavior for market/limit orders.
- Fix incorrect cash movements, security movements, or transaction totals.
- Investigate settlement currency and FX conversion behavior.
- Add guardrails such as insufficient cash or insufficient position checks.
- Update transaction form behavior when route changes affect transaction execution.

## Primary Code Touchpoints
- `src/open_portfolio/transactions.py`
- `src/open_portfolio/accounts.py`
- `src/open_portfolio/web_app.py`
- `tests/test_transactions.py`
- `tests/test_web_app.py`

## Procedure
1. Confirm the expected transaction contract.
- Identify template (`BUY`, `SELL`, `DEPOSIT`, `DIVIDEND`).
- Identify order type (`MARKET`, `LIMIT`) and price source rules.
- Identify currencies involved: product issue currency, settlement currency, portfolio default currency.
- Identify expected movement types and signs.
- Identify position/unit constraints: smallest trading unit, minimum order size, and sellable position.

2. Trace execution path before editing.
- Start at route/form data if issue is UI driven (`web_app.py`).
- Follow into `TransactionManager.create_transaction` and relevant template method.
- Verify exchange-rate source and fallback behavior.
- Verify dependent field reset behavior when instrument or transaction type changes.

3. Implement minimally in domain layer first.
- Keep route handlers thin and push logic into transaction/domain modules when reusable.
- Preserve existing API and enum usage unless requirement explicitly changes.

4. Add or update targeted tests.
- Add transaction unit/regression coverage in `tests/test_transactions.py`.
- Add web flow regression in `tests/test_web_app.py` when behavior is user-facing.

5. Run focused checks, then broader checks.
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_transactions.py -q`
- `PYTHONPATH=src .venv/bin/python -m pytest tests/test_web_app.py -q`
- If transaction behavior affects valuation/report output, run:
  - `PYTHONPATH=src .venv/bin/python -m pytest tests/test_reporting.py -q`

## Validation Checklist
- Movement sign conventions are correct for both cash and security sides.
- Settlement currency account selection is deterministic.
- FX conversion is correct for direct and reverse paths.
- SELL is blocked when position is insufficient.
- Unit and minimum-order validations match instrument configuration.
- Market orders use latest instrument/FX values on or before transaction date when price is needed.
- Limit orders apply percentage semantics for bonds and currency-price semantics for stock/fund/option by default.
- No regression in existing transaction templates.

## Pitfalls
- Import errors when running tests without `PYTHONPATH=src`.
- Logic duplication in Flask route handlers.
- Silent behavior changes when enum names/values are altered.
- Cross-currency flows that pass one path but fail on reverse conversion.
- Inconsistent decimal parsing (`100,23` vs `100.23`) between UI and domain validation.

## References
- `ORDER_ENTRY.md`
