## Order Entry Backlog Register

Datum: 2026-03-29
Status: Actieve gap-registratie voor professionele orderapplicatie

## Doel

- Registreer expliciet alle ontbrekende functies en datapunten in de orderflow.
- Koppel elke gap aan fallback-gedrag in de huidige applicatie.
- Houd implementatie en acceptatiecriteria backlog-ready.

## Gaps

| Gap ID | Titel | Huidige fallback | Impact | Prioriteit | Doelfile(s) |
|---|---|---|---|---|---|
| OE-GAP-001 | Geavanceerde risicolimieten | Alleen basischecks op saldo en positie blokkeren order | Risicobeleid deels afgedekt | Must | src/open_portfolio/web_app.py, src/open_portfolio/transactions.py |
| OE-GAP-002 | Uitgebreid kostenmodel | Standaardkostenmethode voor alle orders | Nettobedrag kan afwijken van broker-executie | Should | src/open_portfolio/transactions.py |
| OE-GAP-003 | Intraday prijsversheid market orders | Laatste koers op of voor transactiedatum | Oude koersen kunnen onbedoeld gebruikt worden | Should | src/open_portfolio/web_app.py, src/open_portfolio/prices.py |
| OE-GAP-004 | Uitgebreide audit actor context | Alleen orderstatus en timestamps | Traceability voor approvals is beperkt | Must | src/open_portfolio/database.py, src/open_portfolio/web_app.py |
| OE-GAP-005 | Persistente order-draft opslag | ✅ Opgeleverd (SQLite DB + retentiebeleid) | N/A | Must | src/open_portfolio/database.py, src/open_portfolio/order_entry.py |

## Voortgang

- OE-GAP-004: gedeeltelijk opgeleverd.
  - Actorvelden (`actor_id`, `actor_role`, `actor_channel`) worden nu meegenomen in conceptorder payload en hervat bij herladen.
  - Restpunt: formele actor-authenticatiebron en goedkeuringsketen koppelen aan definitieve boeking.
- OE-GAP-005: volledig opgeleverd.
  - SQLite schema en repository voor conceptorders zijn aanwezig en getest.
  - App-initialisatie gebruikt nu standaard DB-backed repository met file-based order DB.
  - Opschoning van langlopende conceptorders is geïmplementeerd via retention policy (`OPEN_PORTFOLIO_ORDER_DRAFT_RETENTION_DAYS`, default 30).
  - Monitoringpagina `/order-drafts` toont statusverdeling, recente conceptorders en startup cleanup-resultaat.
  - Handmatige cleanup-actie is beschikbaar op `/order-drafts` met expliciete bevestiging.

## Acceptatiecriteria per gap

### OE-GAP-001
- Risicolimieten zijn configureerbaar per client of portfolio.
- UI onderscheidt blokkade vs waarschuwing.
- Testdekking bevat minimaal grensgevallen voor concentratie en dagnotional.

### OE-GAP-002
- Fee engine ondersteunt percentage en vaste componenten.
- Kosten worden per component getoond in ordersamenvatting.
- Netto-impact sluit aan op boekingsresultaat in transacties.

### OE-GAP-003
- Market order vereist koers binnen configureerbare versheidswindow.
- Bij stale koers wordt order geblokkeerd of vereist expliciete override.
- Meldingen bevatten timestamp van laatst gebruikte koers.

### OE-GAP-004
- Ordermetadata bevat actor-id, rol en kanaal.
- Confirm- en submit-stap leggen actorinformatie vast.
- Auditinformatie is querybaar in datastore.

### OE-GAP-005
- Draft/validated/submitted orders worden persistent opgeslagen.
- Herladen van scherm kan bestaand concept hervatten op draft-id.
- Geen regressie in bestaande directe boekingsflow.

## Traceability

- Deze gaplijst is gekoppeld aan:
  - ORDER_ENTRY.md
  - ORDER_ENTRY_REQUIREMENTS_STRUCTURED.md
  - BACKLOG.md
