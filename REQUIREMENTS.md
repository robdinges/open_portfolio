# Requirements — Bond Portfolio Tool

Datum: 2026-03-29
Status: Werkende baseline (bijgewerkt)

## 1) Scope

Het systeem ondersteunt:

- import van transacties uit broker-CSV,
- beheer van instrumenten op ISIN,
- opslag en beheer van obligatiekoersen en FX,
- portefeuille-waardering en analyse,
- transactiebewerking in spreadsheetstijl,
- persistente opslag in SQLite.

## 2) Functionele requirements

### FR-01 — Eén gedeelde databron

- Alle schermen lezen en schrijven via dezelfde persistente datastore.
- Vereist: SQLite-database met consistente state over sessies.

### FR-02 — Transactie-import (CSV drop)

- Het systeem accepteert transactiebestanden via UI-upload.
- Parsing ondersteunt semicolon-delimited CSV.
- Import filtert op obligaties via `Noteringseenheid = Nominaal`.
- Liquiditeiten- en effectregels met dezelfde `Referentie` worden gekoppeld.
- Voor reconciliatie gebruikt het systeem het transactiebedrag uit de liquiditeitenregel.

### FR-03 — Deduplicatie transacties

- Bij import moet per regel gecontroleerd worden of transactie al bestaat.
- Bestaande transactie: melden + overslaan (geen dubbele boeking).
- Deduplicatie op unieke transactiesleutel (`tx_key`), bij voorkeur op `Referentie`.

### FR-04 — Onbekende ISIN-afhandeling

- Als ISIN bestaat: transactie direct verwerken.
- Als ISIN ontbreekt: instrument eerst aanmaken, daarna transactie verwerken.

### FR-05 — Ondersteunde transactietypen

- Minimaal: `Aankoop`, `Verkoop`, `Coupon betaling`, `Aflossing`, `Deposit`, `Withdrawal`.
- `Aflossing` moet verwerkt worden als verkoop/redemption zonder transactiekosten.
- `Coupon betaling` gebruikt altijd basisvaluta EUR in transactieregistratie.

### FR-06 — Importresultaat en logging

- Na import toont UI minimaal:
  - aantal verwerkt,
  - aantal duplicates overgeslagen,
  - aantal ongeldige regels,
  - aantal nieuw aangemaakte instrumenten.
- Detailmeldingen moeten beschikbaar zijn (uitklapbaar).

### FR-07 — Transactie-overzicht (excel stijl)

- Het systeem biedt een pagina met alle transacties in spreadsheetachtige weergave.
- Filtering op instrument (ISIN) is beschikbaar.
- Inline editing is mogelijk.
- Wijzigingen worden persistent opgeslagen.
- Overzicht toont brokerbedrag, formulebedrag en verschil.

### FR-08 — Koersinvoer obligaties

- Invoer van obligatiekoersen ondersteunt minimaal: `isin`, `datum`, `valuta`, `koers`.
- Duplicate koersrecord: melden + overslaan.

### FR-09 — Koersinvoer valuta

- Invoer van valutakoersen ondersteunt minimaal: `valuta_van`, `valuta_naar`, `datum`, `wisselkoers`.
- Duplicate FX-record: melden + overslaan.

### FR-10 — Single-drop importdetectie

- Eén importdropzone moet bestandstype automatisch herkennen:
  - transacties,
  - positie/koersbestanden.
- Bij ambigu/onbekend: duidelijke foutmelding met verwachte kolommen.

### FR-13 — Formuleberekening transactiebedrag

- Het systeem berekent per transactie een formulebedrag en vergelijkt dit met brokerbedrag.
- Formules:
  - Aankoop/Verkoop: `((A * B * C) + B2) + D`
  - Coupon: `A`
  - Aflossing: `A * B * C`
- Waarbij:
  - `A` = nominaal,
  - `B` = koers (decimaal),
  - `C` = valutakoers,
  - `B2` = opgelopen rente (altijd EUR),
  - `D` = transactiekosten (0,1% van EUR-transactiewaarde, met teken volgens richting).

### FR-14 — Analyse “Verkoop Nu”

- Scenario “Verkoop Nu” bevat:
  - actuele verkoopwaarde,
  - meeverkochte rente,
  - additionele 0,1% transactiekosten.
- Bedragvelden tonen alleen bedragen (geen tekstuele toelichting in hetzelfde veld).

### FR-16 — SELL vs HOLD beslisanalyse (vandaag-vooruit)

- De beslisvergelijking gebruikt alleen cashflows vanaf vandaag.
- Historische coupons worden alleen als context getoond en wegen niet mee in de SELL-vs-HOLD keuze.
- Alle toekomstige cashflows worden contant gemaakt naar vandaag met `discount_rate_percent`.

### FR-17 — Scenarioberekening verkoopprijsband

- SELL-scenario wordt berekend voor drie prijsaannames:
  - `current_price_percent - 0.5%`
  - `current_price_percent`
  - `current_price_percent + 0.5%`
- Verkoopopbrengst bevat opgelopen rente:
  - `sale_proceeds = clean_price + accrued_interest_current`
- Bedragen worden geconverteerd naar EUR via `current_fx_rate` wanneer nodig.

### FR-18 — HOLD tot maturity

- HOLD-scenario bevat:
  - alle resterende coupons,
  - aflossing op 100% nominale waarde op maturity.
- Elke toekomstige cashflowregel toont minimaal:
  - datum,
  - bedrag,
  - discount factor,
  - present value.

### FR-19 — Analyse-output contract

- Analyse levert minimaal deze outputstructuur:
  - `scenario_summary`
  - `sell_results`
  - `hold_results`
  - `discounted_cashflows_table`
  - `final_decision`
- Bij ontbrekende velden retourneert het systeem expliciet `missing_required_inputs` met veldlijst.

### FR-20 — 3D gevoeligheidsanalyse in UI

- Analysepagina toont een 3D-grafiek met opbrengstverschillen (`HOLD - SELL`, EUR):
  - X-as: verkoopprijs `current_price_percent ±1.0%` met stap `0.1%`.
  - Y-as: discount `%` van `0.0` tot `5.0` met stap `0.1%`.
  - Z-as: opbrengstverschil in EUR.

### FR-15 — Instrumentverrijking vanuit transactie

- Bij aanmaken of verrijken van instrumenten:
  - valuta primair uit `Transactiebedrag valuta`,
  - couponpercentage uit naampatroon `(x,xx%)`,
  - einddatum uit naampatroon `dd-mm-jjjj`.

### FR-11 — Positie-overzicht op peildatum

- Positieoverzicht toont posities op gekozen datum.
- Default peildatum = datum van laatst ingelezen obligatiekoers.
- Positie niet tonen als op peildatum nog niet gekocht of volledig verkocht.

### FR-12 — Analysebasis

- Waardering gebruikt transacties + prijzen + FX.
- Rendement en positie-informatie moet reproduceerbaar zijn vanuit DB-state.

### FR-21 — Orderinvoer met instrumenttype-specifieke schermlogica

- Het orderscherm onderscheidt minimaal instrumenttypes: `bond`, `stock`, `option`, `fund`.
- De basisworkflow is voor alle instrumenttypes gelijk:
  - impliciet of expliciet portefeuillecontext bepalen,
  - instrument kiezen (zoekbare dropdown of prefill vanuit holdings),
  - bestaande positie tonen (aantal of nominaal),
  - transactiesoort kiezen (`BUY` of `SELL`),
  - ordertype kiezen (`MARKET` of `LIMIT`),
  - orderhoeveelheid invoeren en direct valideren op handelseenheid en minimale ordergrootte,
  - rekeningselectie en ordersamenvatting tonen,
  - bevestigen of annuleren.

### FR-22 — Veld- en invoerregels orderformulier

- UI toont bij orderhoeveelheid altijd eenheid en minimale ordergrootte van het instrument.
- Voor obligaties wordt nominale waarde ingevoerd en instrumentvaluta achter het veld getoond.
- Voor aandelen wordt aantal stuks ingevoerd zonder valutalabel achter het veld.
- Voor obligaties met `LIMIT` order wordt limiet ingevoerd als percentage (bijv. `100,23` = `100,23%`).
- Voor aandelen met `LIMIT` order wordt limiet ingevoerd als prijs met instrumentvaluta.
- Voor opties en funds geldt voorlopig dezelfde limietnotatie als aandelen, tenzij productconfiguratie expliciet anders aangeeft.

### FR-23 — Rekeningselectie en beschikbare saldi

- Rekeningkeuze is beperkt tot instrumentvaluta en portefeuillevaluta.
- Als instrumentvaluta gelijk is aan portefeuillevaluta:
  - wordt alleen die valutarekening geselecteerd,
  - is wijzigen van rekening niet toegestaan.
- Als instrumentvaluta afwijkt van portefeuillevaluta:
  - controleert systeem of instrumentvalutarekening bestaat,
  - gebruiker kan kiezen tussen instrumentvalutarekening en portefeuillevalutarekening,
  - andere valutarekeningen zijn niet toegestaan.
- Bij elke selecteerbare rekening wordt het actuele beschikbare saldo getoond.

### FR-24 — Berekeningen per order

- Voor obligatieorders wordt meeverkochte of meegekochte rente berekend en getoond.
- Voor elke order worden transactiekosten berekend volgens standaardmethode.
- Voor elke order wordt totaalbedrag per valuta berekend en getoond.
- Indien nodig worden koers en FX bepaald op basis van meest recente waarde op of voor transactiedatum.

### FR-25 — Formuliergedrag, navigatie en input parsing

- Gebruiker kan kiezen voor:
  - bewaren: order opslaan als concept (status DRAFT),
  - bevestigen: order valideren (status VALIDATED),
  - routeren: transactie definitief vastleggen (status SUBMITTED) en navigeren naar transactieoverzicht,
  - annuleren: formulier schonen en navigeren naar vorig scherm.
- Decimalen mogen met komma of punt worden ingevoerd.
- Bij wijziging van instrument worden afhankelijke velden erna geschoond en conditioneel opnieuw getoond.
- Bij wijziging van transactiesoort worden afhankelijke velden erna geschoond en conditioneel opnieuw getoond.
- Herberekening van afgeleide velden vindt plaats bij blur of change, niet bij elke toetsaanslag.
- Het formulier bevat een optioneel geldigheidsdatumveld (`validity_date`) voor de order.

### FR-25a — Instrumentzoeker UX

- Het instrumentveld is een zoekbaar tekstveld met dropdown-suggesties (datalist).
- De gebruiker moet expliciet een suggestie aanklikken om een instrument te selecteren.
- Na selectie wordt het veld read-only en toont het de instrumentnaam.
- Met ESC in zoekmode wordt de vorige selectie hersteld.
- Bij navigatie vanuit holdings is het instrument voorgeselecteerd en vergrendeld.

### FR-26 — Normatieve detailspecificatie orderinvoer

- De volledige normatieve specificatie voor orderinvoer, veldvolgorde, validatieregels en UX-gedrag staat in `ORDER_ENTRY.md`.
- Bij conflict tussen samenvatting in dit document en `ORDER_ENTRY.md` is `ORDER_ENTRY.md` leidend voor orderinvoer.

## 3) Niet-functionele requirements

### NFR-01 — Idempotentie

- Herhaald importeren van hetzelfde bestand mag niet tot dubbele boekingen leiden.

### NFR-02 — Dataconsistentie

- Schermen moeten onderling consistente data tonen.
- Bij inconsistente runtime-state t.o.v. datastore moet waarschuwing mogelijk zijn.

### NFR-03 — Herleidbaarheid

- Import- en wijzigingsacties moeten traceerbaar zijn via keys/logregels.

### NFR-04 — Robuustheid

- Ongeldige records blokkeren de volledige import niet; alleen de betreffende regel wordt overgeslagen met melding.

### NFR-05 — Reproduceerbare reconciliatie

- Berekende velden (`formula_amount`, `amount_difference`) moeten opnieuw afleidbaar zijn via backfill/recompute op bestaande data.

## 4) Datamodel (minimaal)

- `instruments`
- `accounts`
- `transactions`
- `bond_prices`
- `fx_rates`
- `import_log`

## 5) Open punten / vervolgspecificatie

- Definitieve layout voor koersbestanden (obligatie + FX) in productieformaat.
- Exacte businessregels voor maturity-datumvalidatie bij aflossing.
- Formele keuze voor P&L-methodiek (FIFO/LIFO/average cost) voor gerealiseerd resultaat.
