# REQ-05 — Backend: generieke functies en specifieke afwijkingen

Datum: 2026-04-06
Bron: `FEATURES.md`, `web_app.py`, domeinmodules, `ORDER_ENTRY_BACKLOG.md`

---

## 1. Producten en instrumenten

### 1.1 Productmodel

| Regel | Beschrijving | Status |
|---|---|---|
| BE-001 | Basisentiteit `Product` met: instrument_id, description, type (InstrumentType), issue_currency, isin, minimum_purchase_value, smallest_trading_unit. | [IMPL] |
| BE-002 | Afgeleide types: `Stock` (STOCK), `Bond` (BOND + start_date, maturity_date, interest_rate, interest_payment_frequency). | [IMPL] |
| BE-003 | Overige types: OPTION, FUND als generieke Product met InstrumentType-enum. | [IMPL] |
| BE-004 | Producten hebben prijshistorie: lijst van (datum, prijs) tuples. | [IMPL] |
| BE-005 | `get_price(date)`: retourneert meest recente prijs op of vóór de opgegeven datum. | [IMPL] |
| BE-006 | `is_bond()`: controleert of product een obligatie is. | [IMPL] |
| BE-007 | `is_active(on_date)`: controleert of product actief is op datum. | [IMPL] |

### 1.2 Bond-specifiek

| Regel | Beschrijving | Status |
|---|---|---|
| BE-010 | Obligatie heeft verplichte velden: start_date, maturity_date, interest_rate, interest_payment_frequency. | [IMPL] |
| BE-011 | `calculate_accrued_interest(nominal, date, interest_type)`: berekent opgelopen rente. | [IMPL] |
| BE-012 | Couponfrequenties: MONTH, YEAR, END_DATE. | [IMPL] |
| BE-013 | Dag-telconventies: ACT_ACT, THIRTY_360. | [IMPL] |
| BE-014 | Na einddatum is obligatie inactief. | [IMPL] |

### 1.3 ProductCollection

| Regel | Beschrijving | Status |
|---|---|---|
| BE-020 | Registry van producten op instrument_id. | [IMPL] |
| BE-021 | `add_product()`: voegt toe of overschrijft bestaand product. | [IMPL] |
| BE-022 | `search_product_id(id)`: zoekt product op ID, retourneert None als niet gevonden. | [IMPL] |
| BE-023 | `list_products(include_inactive, on_date)`: gefilterde lijst, gesorteerd. | [IMPL] |

## 2. Transactiemotor

### 2.1 TransactionManager

| Regel | Beschrijving | Status |
|---|---|---|
| BE-030 | `create_transaction(template, ...)`: maakt transactie aan volgens template (BUY, SELL, DEPOSIT, DIVIDEND). | [IMPL] |
| BE-031 | `execute_transaction(tx, portfolio, product_collection)`: voert transactie uit met validatie. | [IMPL] |
| BE-032 | `create_and_execute_transaction(...)`: gecombineerde convenience-methode. | [IMPL] |
| BE-033 | Validatie bij uitvoering: saldocheck per kasrekening; debetsaldo blokkeert. | [IMPL] |

### 2.2 Movements

| Regel | Beschrijving | Status |
|---|---|---|
| BE-040 | `CashMovement`: bevat cash_account_id, amount, currency, movement_type, exchange_rate. | [IMPL] |
| BE-041 | `SecurityMovement`: bevat product_id, amount_nominal, price, movement_type. | [IMPL] |
| BE-042 | Transaction bevat lijsten van cash_movements en security_movements. | [IMPL] |
| BE-043 | `to_dict()`: serialize naar woordenboek voor weergave en opslag. | [IMPL] |

### 2.3 BUY-template specifiek

| Regel | Beschrijving | Status |
|---|---|---|
| BE-050 | SecurityMovement met type SECURITY_BUY. | [IMPL] |
| BE-051 | CashMovement voor effectenwaarde (negatief, type SECURITY_BUY). | [IMPL] |
| BE-052 | CashMovement voor transactiekosten (negatief, type COSTS). | [IMPL] |
| BE-053 | Bij obligaties: CashMovement voor opgelopen rente (type ACCRUED_INTEREST). | [IMPL] |
| BE-054 | Bij afwijkende valuta: FX-conversie naar afrekenvaluta. | [IMPL] |

### 2.4 SELL-template specifiek

| Regel | Beschrijving | Status |
|---|---|---|
| BE-060 | SecurityMovement met type SECURITY_SELL (negatief nominaal). | [IMPL] |
| BE-061 | CashMovement voor verkoopopbrengst (positief, type SECURITY_SELL). | [IMPL] |
| BE-062 | Positiecheck: beschikbare hoeveelheid moet voldoende zijn. | [IMPL] |

## 3. Portfoliobeheer

### 3.1 Portfolio

| Regel | Beschrijving | Status |
|---|---|---|
| BE-070 | Portfolio bevat: portfolio_id, name, default_currency, cash_accounts, securities_account. | [IMPL] |
| BE-071 | `cash_accounts`: dictionary met key (account_id, currency, account_type). | [IMPL] |
| BE-072 | `securities_account`: bevat holdings als lijst van {product, amount} dicts. | [IMPL] |
| BE-073 | `list_all_transactions()`: retourneert geserialiseerde transacties uit alle kasrekeningen, gededupliceerd op transaction_number. | [IMPL] |
| BE-074 | `search_account_id(id, currency)`: zoekt kasrekening op ID en valuta. | [IMPL] |

### 3.2 Client

| Regel | Beschrijving | Status |
|---|---|---|
| BE-080 | Client bevat: client_id, name, portfolios (lijst). | [IMPL] |
| BE-081 | Meerdere portefeuilles per client ondersteund. | [IMPL] |

## 4. Pricing

### 4.1 Productprijzen

| Regel | Beschrijving | Status |
|---|---|---|
| BE-090 | Prijzen worden per product opgeslagen als (datum, prijs) paren. | [IMPL] |
| BE-091 | `get_price(date)`: retourneert meest recente prijs ≤ date, of None. | [IMPL] |

### 4.2 FX-pricing

| Regel | Beschrijving | Status |
|---|---|---|
| BE-095 | CurrencyPrices: mapping van (valutapaar, datum) naar wisselkoers. | [IMPL] |
| BE-096 | Reverse FX: als directe koers ontbreekt, gebruik 1/reverse. | [IMPL] |
| BE-097 | Identische valuta: FX = 1.0 zonder lookup. | [IMPL] |

## 5. Order lifecycle

### 5.1 OrderDraft

| Regel | Beschrijving | Status |
|---|---|---|
| BE-100 | OrderDraft bevat: draft_id, status, payload, errors, warnings, created_at, updated_at. | [IMPL] |
| BE-101 | Statussen: DRAFT, VALIDATED, REJECTED, SUBMITTED. | [IMPL] |
| BE-102 | Payload bevat alle orderinvoervelden als woordenboek. | [IMPL] |
| BE-103 | Bestaand concept hervatten via draft-id in URL. | [IMPL] |

### 5.2 Repository

| Regel | Beschrijving | Status |
|---|---|---|
| BE-110 | `upsert_draft(payload, draft_id, status, warnings, errors)`: maakt aan of werkt bij. | [IMPL] |
| BE-111 | `get_draft(draft_id)`: haalt concept op. | [IMPL] |
| BE-112 | `set_status(draft_id, status)`: wijzigt alleen de status. | [IMPL] |

### 5.3 Retentiebeleid

| Regel | Beschrijving | Status |
|---|---|---|
| BE-120 | Bij app-start: verwijder conceptorders ouder dan configureerbare retentie (default 30 dagen). | [IMPL] |
| BE-121 | Configureerbaar via environment variable `OPEN_PORTFOLIO_ORDER_DRAFT_RETENTION_DAYS`. | [IMPL] |
| BE-122 | Handmatige opschoningsactie beschikbaar op /order-drafts met bevestiging. | [IMPL] |

## 6. Database (SQLite)

| Regel | Beschrijving | Status |
|---|---|---|
| BE-130 | Tabellen: client, portfolio, order_draft, instrument. | [IMPL] |
| BE-131 | Thread-safe wrapper (connection per call). | [IMPL] |
| BE-132 | `upsert_instrument()`: slaat instrumentdefinities persistent op. | [IMPL] |
| BE-133 | `list_instruments()`: laadt alle instrumenten bij app-start. | [IMPL] |
| BE-134 | Bestaande marktdata (prijzen, transacties) worden behouden bij instrument-update uit DB. | [IMPL] |

## 7. Orderservice (refactored)

| Regel | Beschrijving | Status |
|---|---|---|
| BE-140 | `validate_and_calculate_order(...)`: centrale validatie- en berekeningsmethode. | [IMPL] |
| BE-141 | `parse_decimal`, `parse_optional_decimal`, `parse_tx_date`: inputparsing. | [IMPL] |
| BE-142 | `get_fx(from, to)`: FX-ophalen met reverse fallback. | [IMPL] |
| BE-143 | `get_position_map(portfolio)`: positie per product als dict. | [IMPL] |
| BE-144 | `build_settlement_options(portfolio, product)`: geeft toegestane afrekenmuntrekeningen. | [IMPL] |
| BE-145 | `is_multiple_of_unit(amount, unit)`: controleert handelseenheid. | [IMPL] |
| BE-146 | `get_latest_price_for_date(product, date)`: koers ophalen met datum. | [IMPL] |
| BE-147 | `calculate_cost(amount)`: standaardkostenberekening. | [IMPL] |
| BE-148 | `product_kind(product)`: retourneert "bond", "stock", "option" of "fund". | [IMPL] |

## 8. Specifieke afwijkingen en fallbacks

| Regel | Beschrijving | Fallback | Status |
|---|---|---|---|
| BE-200 | Risicolimieten (OE-GAP-001) | Alleen basis saldo- en positiechecks | [GAP] |
| BE-201 | Kostenmodel per venue (OE-GAP-002/006) | Vast 0,1% voor alle orders | [GAP] |
| BE-202 | Intraday prijsversheid (OE-GAP-003) | Laatste koers op of voor tx-datum | [GAP] |
| BE-203 | Audit actor context (OE-GAP-004) | Actor-velden in payload, geen formele audit trail | [GAP] |
| BE-204 | Opgelopen rente op settlementdatum (OE-GAP-007) | Berekening op transactiedatum | [GAP] |
| BE-205 | Ex-coupon waarschuwing (OE-GAP-008) | Geaccepteerd zonder waarschuwing | [GAP] |

## 9. Demodata en testdata

| Regel | Beschrijving | Status |
|---|---|---|
| BE-300 | `create_realistic_dataset()`: laadt complete dataset uit `data/*.json`. | [IMPL] |
| BE-301 | 2 clients, 3 portefeuilles, 27 producten, 10 transacties, prijshistorie, FX-koersen. | [IMPL] |
| BE-302 | Demodata wordt automatisch geladen bij app-start als geen externe data is meegegeven. | [IMPL] |
| BE-303 | JSON-databestanden: clients.json, portfolios.json, products.json, prices.json, currency_prices.json, cash_accounts.json, transactions.json. | [IMPL] |
