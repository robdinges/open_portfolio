# Backlog (Must / Should / Could)

Datum: 2026-03-29

## Reeds opgeleverd

- Multi-file import met typeherkenning (transacties/positie).
- Transactie-overzicht met edit/save + soft delete.
- Import auditlog in DB.
- Referentie-koppeling effecten/liquiditeiten voor brokerbedrag.
- Formulebedrag + verschillenmonitoring in UI.
- Couponvaluta-normalisatie (`EUR`, `fx_rate=1.0`).
- Instrumentverrijking vanuit transactie (valuta, coupon %, einddatum uit naam).
- Tijdelijke DB-resetknop in UI.
- Analyse "Verkoop Nu" met meeverkochte rente en 0,1% kosten.
- Nieuwe SELL-vs-HOLD beslismodule (`BondPosition`, `BondCalculator`,
  `compare_scenarios`).
- Order lifecycle persistentie (Draft/Validated/Submitted) in SQLite met
  retentiebeleid en monitoringpagina.
- Instrument lifecycle persistentie: add/edit/save schrijft naar SQLite;
  bij app-start worden instrumentwijzigingen uit DB teruggeladen.
- Orderinvoerformulier met grid-layout, instrumentzoeker, positie-indicator,
  kostencalculatie, opgelopen rente, FX-conversie, geldigheidsdatum en
  draft/validate/submit-workflow.
- Rekeningselectie met valutaregels: automatisch vergrendeld bij gelijke
  valuta, keuze uit instrument- of portefeuillevaluta bij afwijkende valuta.
- Marktkoers-preview bij instrumentselectie (actuele koers met datum).
- Blur/change-only recalculatie (geen herberekening bij elke toetsaanslag).
- Instrumentzoeker UX: expliciet klikken om te selecteren, ESC om
  vorige selectie te herstellen, read-only na selectie.


## Must

1. **Geautomatiseerde tests (expliciet uitgesteld)**
   - Unit-tests voor import-validatie, replay en transactiebewerkingen.
   - Integratietest voor SQLite-replay na edit/delete.

2. **Startup health-check gate (expliciet uitgesteld)**
   - Valideer schema, verplichte tabellen en kernconfiguratie bij startup.
   - Blokkeer app-start met duidelijke foutdiagnose bij kritieke
     inconsistentie.

3. **Service-laag refactor (expliciet uitgesteld)**
   - Splits `app.py` op in UI, services en repository laag.
   - Verminder session-state koppeling in domeinlogica.

4. **Audit actor context voor orders**
   - Leg order-actor metadata vast (gebruiker, rol, kanaal, referentie).
   - Koppel actor metadata aan bevestiging en definitieve boeking.
   - Status: gedeeltelijk opgeleverd; actorvelden zitten in draft payload
     maar zijn nog niet gekoppeld aan een formele audit trail.

5. **Koersimportbestanden (batch) naar DB**
   - Batch-import valutakoersen met duplicate-skip (transactiegebaseerd
     en extern).

6. **Positie-overzicht op peildatum**
   - Nieuwe pagina met positie op datum.
   - Default datum = laatste obligatiekoersdatum.

7. **Rebuild/replay validatie na edits**
   - Volledige portfolio-replay na transactiewijziging met
     integriteitschecks.

## Should

1. **Datastatus blok in UI**
   - Recordcounts per tabel (`instruments`, `transactions`, `bond_prices`,
     `fx_rates`).

2. **Consistentiewaarschuwingen**
   - Signaal als runtime-cache en DB niet synchroon zijn.

3. **Import auditlog**
   - Tabel met importruns: timestamp, file, verwerkt/skipped/errors.

4. **Instrument governance**
   - Markering "incompleet instrument" bij auto-create op basis van
     transactie.

5. **Gesimuleerde toekomstige cashflows per selectie**
   - Genereer per run toekomstige transacties (coupon + aflossing) vanaf
     de laatst ingelezen transactie.
   - Berekening moet gebeuren voor de op dat moment geselecteerde
     obligaties in de tijdlijn.
   - Neem deze toekomstige datums mee in de periode-slider zodat
     historische + verwachte cashflows in één venster zichtbaar zijn.

6. **Werklijst na inleesactie voor ontbrekende instrumentdata**
   - Maak direct na import een werklijst met instrumenten waarvoor
     verplichte velden ontbreken.
   - Werk deze lijst iteratief af totdat alle benodigde data gevuld is.
   - Minimaal te vullen velden: coupondatum, startdatum, einddatum,
     couponrentepercentage.

7. **Afrondingsbeleid reconciliatie**
   - Formele keuze wanneer tussenstappen op 2 decimalen afgerond worden.
   - Uniforme afrondingsregels voor brokervergelijking en
     scenario-uitkomsten.

8. **Analyse-export naar Excel**
   - Downloadknop op Analysepagina voor directe export van alle
     beslisatabellen.
   - Vaste tabbladnaam `Analyse` en kolomvolgorde consistent met UI.

9. **Order Entry placeholders afronden**
   - OE-GAP-001: geavanceerde risicolimieten
     (concentratie/dagnotional/trader).
   - OE-GAP-002: uitgebreid kostenmodel
     (broker/beurs/vaste componenten).
   - OE-GAP-003: intraday prijsversheid voor market orders.
   - OE-GAP-004: uitgebreide audit actor context.

## Could

1. **Rendementsmodule TWR/MWR**
   - TWR op periodisering en MWR/XIRR op cashflows.

2. **Couponkalender / cashflow forecast**
   - Verwachte coupon- en aflossingsstromen.

3. **Duration / convexity + scenarioanalyse**
   - Renteschok en impact op portefeuille.

4. **Valutablootstelling en hedge-overzicht**
   - Exposures per valuta en geaggregeerde effecten.

5. **Analysepagina** met transparante tabellen (input, sale, coupon
   schedule, discounted cashflows, final decision).

---

## Analyse: tegenstrijdigheden, ongebruikte functies en redundantie

Datum: 2026-04-06

### A. Tegenstrijdigheden tussen requirements en realisatie

| # | Locatie | Requirement | Realisatie | Ernst |
|---|---|---|---|---|
| C-001 | `transactions.py:271`, `enums.py` | REQ-01 WD-060: dividend → "Dividend"; REQ-04 BR-103: DIVIDEND-template produceert dividend-beweging. | `_dividend_template` gebruikt `MovementType.INTEREST` (waarde `interest`). Er bestaat geen `MovementType.DIVIDEND` in het enum. Dividenden tonen daardoor als "interest" (geen vertaling) in plaats van "Dividend". | Hoog |
| C-002 | `templates/holdings.html:22` | REQ-03 SHO-005: instrumenttype vertaald via `translate_instrument_type`. | Template roept `translate_instrument_type(h.product.__class__.__name__)` aan. Dit levert klassenamen ("Product", "Bond", "Stock") i.p.v. enum-waarden ("STOCK", "BOND"). De vertaalfunctie heeft fallback-mappings voor "Stock" en "Bond" maar niet voor "Product" — generieke producten (OPTION, FUND) tonen als klassenaam. | Middel |
| C-003 | `templates/holdings.html:20` | REQ-03 SHO-007: kolom Prijs toont actuele koers. | Template verwijst naar `h.last_price` die nooit gezet wordt op holdings-dicts (`{"product": ..., "amount": ...}`). Jinja `is defined`-check is altijd False → fallback `h.product.get_price(valuation_date)` werkt, maar de dode code verbergt een ontwerp-mismatch. | Laag |
| C-004 | `enums.py` | REQ-01 WD-060: vertaaltabel bevat "dividend" → "Dividend". | `MovementType` enum kent geen `DIVIDEND`-waarde. De vertaling in `translate_movement_type` voor "dividend" wordt nooit bereikt. | Hoog (gekoppeld aan C-001) |
| C-005 | `web_app.py:91-103` | REQ-01 WD-050: vertalingen voor alle instrumenttypen (STOCK, BOND, OPTION, FUND). | `translate_instrument_type` bevat extra fallbacks voor Python-klassenamen ("Stock", "Bond") die niet in requirements staan. Dit maskeert het eigenlijke probleem (C-002) in plaats van het op te lossen. | Laag |

### B. Ongebruikte backend-functies

| # | Functie / klasse | Locatie | Aangeroepen vanuit | Toelichting |
|---|---|---|---|---|
| U-001 | `Portfolio.list_accounts()` | `accounts.py:151` | Alleen `portfolio_sim.ipynb` | Console-printmethode, niet gebruikt in webapplicatie. |
| U-002 | `Portfolio.list_holdings()` | `accounts.py:166` | Alleen `portfolio_sim.ipynb` | Console-printmethode met eigen positionering-logica; web gebruikt `securities_account.holdings` rechtstreeks. |
| U-003 | `Portfolio.list_transactions()` | `accounts.py:210` | Nergens | Console-printmethode, zelfs niet in notebook. Dubbelt met `list_all_transactions()` die wél overal wordt gebruikt. |
| U-004 | `CurrencyPrices.show_prices()` | `prices.py:31` | Nergens | Debug-printmethode zonder aanroepers. |
| U-005 | `ProductPrices.show_prices()` | `prices.py:47` | Nergens | Debug-printmethode zonder aanroepers. |
| U-006 | `ProductPrices` (klasse) | `prices.py:35` | Nergens geïnstantieerd | Geëxporteerd in `__init__.py` maar nooit aangemaakt; prijzen zitten op `Product`-objecten. |
| U-007 | `InMemoryOrderRepository` | `order_entry.py:37` | Nergens in productie | Vervangen door `DatabaseOrderRepository`; enkel nog in `__init__.py` export. |
| U-008 | `QuotationType` enum | `enums.py:11` | Nergens | Gedefinieerd maar nooit gebruikt in code. |
| U-009 | `TransactionType` enum | `enums.py:15` | Nergens | Gedefinieerd maar nooit gebruikt in code. |
| U-010 | `AccountType.OBLIGO` enum-waarde | `enums.py:30` | Nergens | Enumwaarde zonder enig gebruik. |

### C. Redundante logica

| # | Locatie 1 | Locatie 2 | Beschrijving | Aanbeveling |
|---|---|---|---|---|
| R-001 | `web_app.py:233` `parse_float()` | `order_service.py:12` `parse_decimal()` | Identieke logica: strip, vervang komma→punt, float-conversie, zelfde foutmeldingen. `web_app.py` importeert `parse_decimal` als `os_parse_decimal` maar definieert daarnaast een eigen `parse_float`. | Verwijder `parse_float()`; gebruik `os_parse_decimal` overal. |
| R-002 | `accounts.py:166` `list_holdings()` | `templates/holdings.html` | `list_holdings()` berekent posities via transaction-replay; de webpagina gebruikt `securities_account.holdings` rechtstreeks. Twee verschillende mechanismen voor dezelfde data. | Verwijder `list_holdings()` of documenteer als notebook-only. |
| R-003 | `accounts.py:210` `list_transactions()` | `accounts.py:136` `list_all_transactions()` | `list_transactions()` roept `list_all_transactions()` aan en formatteert naar console. Dezelfde data, extra laag. | Verwijder `list_transactions()` (is al nergens aangeroepen). |
| R-004 | `translate_instrument_type()`: mappings voor enum-waarden ("STOCK", "BOND") **plus** klassenamen ("Stock", "Bond") | — | Twee sets sleutels voor hetzelfde doel. Klassenaam-mappings zijn een workaround voor het feit dat `holdings.html` `__class__.__name__` doorgeeft i.p.v. `product.type`. | Gebruik `product.type.value` of `product.type.name` in template; verwijder klassenaam-fallbacks uit vertaalfunctie. |
