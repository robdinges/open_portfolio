# Backlog (Must / Should / Could)

Datum: 2026-03-07

## Reeds opgeleverd

- Multi-file import met typeherkenning (transacties/positie).
- Transactie-overzicht met edit/save + soft delete.
- Import auditlog in DB.
- Referentie-koppeling effecten/liquiditeiten voor brokerbedrag.
- Formulebedrag + verschillenmonitoring in UI.
- Couponvaluta-normalisatie (`EUR`, `fx_rate=1.0`).
- Instrumentverrijking vanuit transactie (valuta, coupon %, einddatum uit naam).
- Tijdelijke DB-resetknop in UI.
- Analyse “Verkoop Nu” met meeverkochte rente en 0,1% kosten.
- Nieuwe SELL-vs-HOLD beslismodule (`BondPosition`, `BondCalculator`, `compare_scenarios`).


## Must

1. **Geautomatiseerde tests (expliciet uitgesteld)**
   - Unit-tests voor import-validatie, replay en transactiebewerkingen.
   - Integratietest voor SQLite-replay na edit/delete.

2. **Startup health-check gate (expliciet uitgesteld)**
   - Valideer schema, verplichte tabellen en kernconfiguratie bij startup.
   - Blokkeer app-start met duidelijke foutdiagnose bij kritieke inconsistentie.

3. **Service-laag refactor (expliciet uitgesteld)**
   - Splits `app.py` op in UI, services en repository laag.
   - Verminder session-state koppeling in domeinlogica.

4. **Order lifecycle persistentie (Draft/Validated/Submitted)**
   - Persistente opslag van conceptorders met status, timestamps en validatieresultaten.
   - Vervang tijdelijke in-memory opslag in order flow door DB-backed repository.

5. **Audit actor context voor orders**
   - Leg order-actor metadata vast (gebruiker, rol, kanaal, referentie).
   - Koppel actor metadata aan bevestiging en definitieve boeking.

4. **Koersimportbestanden (batch) naar DB**
   - Batch-import valutakoersen met duplicate-skip (transactiegebaseerd en extern).

5. **Positie-overzicht op peildatum**
   - Nieuwe pagina met positie op datum.
   - Default datum = laatste obligatiekoersdatum.

6. **Rebuild/replay validatie na edits**
   - Volledige portfolio-replay na transactiewijziging met integriteitschecks.

7. **Format input screen**

## Should

1. **Datastatus blok in UI**
   - Recordcounts per tabel (`instruments`, `transactions`, `bond_prices`, `fx_rates`).

2. **Consistentiewaarschuwingen**
   - Signaal als runtime-cache en DB niet synchroon zijn.

3. **Import auditlog**
   - Tabel met importruns: timestamp, file, verwerkt/skipped/errors.

4. **Instrument governance**
   - Markering “incompleet instrument” bij auto-create op basis van transactie.

5. **Gesimuleerde toekomstige cashflows per selectie**
   - Genereer per run toekomstige transacties (coupon + aflossing) vanaf de laatst ingelezen transactie.
   - Berekening moet gebeuren voor de op dat moment geselecteerde obligaties in de tijdlijn.
   - Neem deze toekomstige datums mee in de periode-slider zodat historische + verwachte cashflows in één venster zichtbaar zijn.

6. **Werklijst na inleesactie voor ontbrekende instrumentdata**
   - Maak direct na import een werklijst met instrumenten waarvoor verplichte velden ontbreken.
   - Werk deze lijst iteratief af totdat alle benodigde data gevuld is.
   - Minimaal te vullen velden: coupondatum, startdatum, einddatum, couponrentepercentage.

7. **Afrondingsbeleid reconciliatie**
   - Formele keuze wanneer tussenstappen op 2 decimalen afgerond worden.
   - Uniforme afrondingsregels voor brokervergelijking en scenario-uitkomsten.

8. **Analyse-export naar Excel**
   - Downloadknop op Analysepagina voor directe export van alle beslisatabellen.
   - Vaste tabbladnaam `Analyse` en kolomvolgorde consistent met UI.

9. **Order Entry placeholders afronden**
   - OE-GAP-001: geavanceerde risicolimieten (concentratie/dagnotional/trader).
   - OE-GAP-002: uitgebreid kostenmodel (broker/beurs/vaste componenten).
   - OE-GAP-003: intraday prijsversheid voor market orders.
   - OE-GAP-004: uitgebreide audit actor context.

10. **Instrument lifecycle persistentie (opgeleverd)**
   - Add/edit/save op instrumentscherm schrijft nu naar SQLite.
   - Bij app-start worden instrumentwijzigingen uit DB teruggeladen in de productcollectie.

## Could

1. **Rendementsmodule TWR/MWR**
   - TWR op periodisering en MWR/XIRR op cashflows.

2. **Couponkalender / cashflow forecast**
   - Verwachte coupon- en aflossingsstromen.

3. **Duration / convexity + scenarioanalyse**
   - Renteschok en impact op portefeuille.

4. **Valutablootstelling en hedge-overzicht**
   - Exposures per valuta en geaggregeerde effecten.

5. **Analysepagina** met transparante tabellen (input, sale, coupon schedule, discounted cashflows, final decision).