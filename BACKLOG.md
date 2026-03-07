# Backlog (Must / Should / Could)

Datum: 2026-03-06

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

4. **Koersimportbestanden (batch) naar DB**
   - Batch-import valutakoersen met duplicate-skip (transactiegebaseerd en extern).

5. **Positie-overzicht op peildatum**
   - Nieuwe pagina met positie op datum.
   - Default datum = laatste obligatiekoersdatum.

6. **Rebuild/replay validatie na edits**
   - Volledige portfolio-replay na transactiewijziging met integriteitschecks.

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

## Could

1. **Rendementsmodule TWR/MWR**
   - TWR op periodisering en MWR/XIRR op cashflows.

2. **Couponkalender / cashflow forecast**
   - Verwachte coupon- en aflossingsstromen.

3. **Duration / convexity + scenarioanalyse**
   - Renteschok en impact op portefeuille.

4. **Valutablootstelling en hedge-overzicht**
   - Exposures per valuta en geaggregeerde effecten.
