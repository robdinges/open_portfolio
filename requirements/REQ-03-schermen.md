# REQ-03 — Specifieke requirements per scherm (tab)

Datum: 2026-04-06
Bron: templates, `web_app.py`, `.github/instructions.md`, chatinstructies

---

## 1. Home (`/`)

### 1.1 Doel
Centraal startpunt voor client- en portefeuilleselectie.

### 1.2 Elementen

| Regel | Beschrijving | Status |
|---|---|---|
| SH-001 | Kop: "Selecteer portefeuille". | [IMPL] |
| SH-002 | Client-selectie via dropdown. Wijziging triggert directe verversing. | [IMPL] |
| SH-003 | Geen duplicaatweergave van geselecteerde client onder het keuzeveld. De dropdown is voldoende. | [IMPL] |
| SH-004 | Portefeuilletabel bevat kolommen: ID & Omschrijving, Totaal cash saldo, Acties. | [IMPL] |
| SH-005 | Portefeuille-ID en naam getoond als klikbare link naar Holdings. Formaat: `id – naam`. | [IMPL] |
| SH-006 | Totaal cash saldo toont som van saldi in portefeuillebasisvaluta. Format: `format_currency`. | [IMPL] |
| SH-007 | Acties per portefeuille: knoppen "Nieuwe transactie" en "Cash accounts". | [IMPL] |
| SH-008 | Alle links behouden client_id en portfolio_id als queryparameters. | [IMPL] |
| SH-009 | Portefeuilletabel alleen zichtbaar als er een client is geselecteerd. | [IMPL] |

---

## 2. Cash Accounts (`/accounts`)

### 2.1 Doel
Overzicht van kasrekeningen bij de geselecteerde portefeuille.

### 2.2 Elementen

| Regel | Beschrijving | Status |
|---|---|---|
| SA-001 | Kop: "Cash Accounts". | [IMPL] |
| SA-002 | Context-grid: Klant, Portefeuille, Portefeuille-id. | [IMPL] |
| SA-003 | Tabel met kolommen: Currency, Type, Balance. | [IMPL] |
| SA-004 | Balance rechts uitgelijnd met `format_currency`. | [IMPL] |
| SA-005 | Type toont de naam van het accounttype-enum. | [IMPL] |

---

## 3. Holdings (`/holdings`)

### 3.1 Doel
Effectenposities in de geselecteerde portefeuille.

### 3.2 Elementen

| Regel | Beschrijving | Status |
|---|---|---|
| SHO-001 | Kop: "Holdings". | [IMPL] |
| SHO-002 | Context-grid: Klant, Portefeuille, Portefeuille-id. | [IMPL] |
| SHO-003 | Tabel met kolommen: ISIN, Naam, Type, Valuta, Aantal / Nominaal, Prijs, Acties. | [IMPL] |
| SHO-004 | ISIN kolom: toont ISIN van het product, of `-` als leeg. | [IMPL] |
| SHO-005 | Type: vertaald via `translate_instrument_type` (Aandeel, Obligatie). | [IMPL] |
| SHO-006 | Aantal: voor aandelen `format_quantity` zonder suffix. Voor obligaties `format_quantity` + instrumentvaluta. | [IMPL] |
| SHO-007 | Prijs: voor obligaties als percentage met `%`. Voor aandelen als `format_currency`. | [IMPL] |
| SHO-008 | Prijs gebruikt `h.last_price` indien gedefinieerd, anders `h.product.get_price(valuation_date)`. | [IMPL] |
| SHO-009 | Actieknoppen per holding: "B" (Buy) en "S" (Sell) als compacte knoppen (`.button-sm`). | [IMPL] |
| SHO-010 | Buy/Sell knoppen navigeren naar orderformulier met prefill: client_id, portfolio_id, product_id, template, return_to=holdings. | [IMPL] |
| SHO-011 | Als tabel leeg: melding "Geen holdings voor deze portefeuille." met juiste colspan. | [IMPL] |
| SHO-012 | Tabel wordt niet getoond als geen portefeuille is geselecteerd. | [IMPL] |

---

## 4. Transacties (`/transactions`)

### 4.1 Doel
Overzicht van alle uitgevoerde transacties in de geselecteerde portefeuille.

### 4.2 Elementen

| Regel | Beschrijving | Status |
|---|---|---|
| ST-001 | Kop: "Transacties". | [IMPL] |
| ST-002 | Context-grid: Klant, Portefeuille, Portefeuille-id. | [IMPL] |
| ST-003 | Tabel met kolommen: Datum, Type, ISIN, Naam, Aantal, Prijs, Cashrekening, Totaal (cash valuta). | [IMPL] |
| ST-004 | Transacties gesorteerd op datum, nieuwste bovenaan. | [IMPL] |
| ST-005 | Type: vertaald via `translate_movement_type` (Aankoop, Verkoop, etc.). | [IMPL] |
| ST-006 | ISIN: toont ISIN van het product, of `-` als niet beschikbaar. | [IMPL] |
| ST-007 | Naam: toont `product.description`, of `product_id` als product niet gevonden. | [IMPL] |
| ST-008 | Aantal: `format_quantity`. Voor obligaties met instrumentvaluta-suffix. Voor aandelen zonder suffix. | [IMPL] |
| ST-009 | Prijs: voor obligaties als percentage met `%`. Voor aandelen als `format_currency`. | [IMPL] |
| ST-010 | Cashrekening: toont alleen de valutacode (bijv. EUR), niet het rekening-id. | [IMPL] |
| ST-011 | Totaal: `format_currency` van de som van relevante cash movements (security_buy, security_sell, costs, accrued_interest). | [IMPL] |
| ST-012 | Transacties zonder security_movements tonen `-` in alle velden. | [IMPL] |
| ST-013 | Als tabel leeg: melding "Geen transacties voor deze portefeuille." | [IMPL] |

---

## 5. Orderinvoer (`/transactions/new`)

### 5.1 Doel
Volledig transactieformulier met draft/validate/submit workflow.

### 5.2 Contextweergave

| Regel | Beschrijving | Status |
|---|---|---|
| SO-001 | Context-header toont: Portefeuille (naam + id), Orderstatus, Eigenaar, Datum. | [IMPL] |
| SO-002 | Orderstatus toont `Nieuw` bij verse orders, of de huidige draft-status. | [IMPL] |
| SO-003 | Bij bestaand concept wordt draft-id getoond naast de status. | [IMPL] |

### 5.3 Formuliervelden

| Regel | Beschrijving | Status |
|---|---|---|
| SO-010 | Transactiesoort: dropdown met BUY en SELL opties. | [IMPL] |
| SO-011 | Ordertype: dropdown met MARKET en LIMIT opties. Standaard MARKET. | [IMPL] |
| SO-012 | Instrument: zoekbaar tekstveld met dropdown-suggesties (datalist). | [IMPL] |
| SO-013 | Na instrumentselectie wordt veld read-only en toont het instrument-label. | [IMPL] |
| SO-014 | ESC in zoekmode herstelt de vorige selectie. | [IMPL] |
| SO-015 | Bij navigatie vanuit holdings: instrument voorgeselecteerd en vergrendeld. | [IMPL] |
| SO-016 | Aantal: label varieert per instrumenttype ("Aantal" voor aandelen, "Nominale waarde" voor obligaties). | [IMPL] |
| SO-017 | Bij obligaties: instrumentvaluta-suffix achter het hoeveelheidsveld. | [IMPL] |
| SO-018 | Limietprijs: alleen zichtbaar bij LIMIT-orders. | [IMPL] |
| SO-019 | Limietprijs-suffix: `%` voor obligaties, instrumentvaluta voor aandelen. | [IMPL] |
| SO-020 | Geldigheidsdatum: optioneel datumveld, alleen zichtbaar bij LIMIT-orders. | [IMPL] |
| SO-021 | Afrekenen op: dropdown met toegestane rekeningen (instrumentvaluta, portefeuillevaluta). | [IMPL] |
| SO-022 | Bij gelijke instrument- en portefeuillevaluta: rekening automatisch vergrendeld. Tekst: "Vast op portefeuillevaluta". | [IMPL] |
| SO-023 | Bij elke rekening wordt het beschikbare saldo getoond. | [IMPL] |

### 5.4 Informatiepaneel (rechts)

| Regel | Beschrijving | Status |
|---|---|---|
| SO-030 | Positie: huidige hoeveelheid van het instrument in de portefeuille. | [IMPL] |
| SO-031 | Handelseenheid en minimale ordergrootte getoond als referentie. | [IMPL] |
| SO-032 | Actuele koers met datum getoond na instrumentselectie. | [IMPL] |
| SO-033 | Brutobedrag, transactiekosten, opgelopen rente (alleen bonds), orderbedrag. | [IMPL] |
| SO-034 | Alle bedragen in `format_currency` met afrekenmuntvaluta. | [IMPL] |
| SO-035 | Opgelopen rente alleen zichtbaar voor obligaties. | [IMPL] |

### 5.5 Actieknoppen

| Regel | Beschrijving | Status |
|---|---|---|
| SO-040 | "Concept opslaan": slaat order op als DRAFT. Gebruiker blijft op formulier. | [IMPL] |
| SO-041 | "Valideren": valideert en zet status op VALIDATED. Gebruiker blijft op formulier. | [IMPL] |
| SO-042 | "Routeren": definitief boeken (SUBMITTED). Redirect naar transactieoverzicht. | [IMPL] |
| SO-043 | "Annuleren": schoon formulier, navigeer naar vorig scherm. | [IMPL] |
| SO-044 | Bij return_to=holdings navigeert annuleren terug naar Holdings met context. | [IMPL] |

### 5.6 Dynamisch formuliergedrag

| Regel | Beschrijving | Status |
|---|---|---|
| SO-050 | Bij wijziging instrument: alle afhankelijke velden wissen en opnieuw opbouwen. | [IMPL] |
| SO-051 | Bij wijziging transactiesoort: afhankelijke velden wissen en opnieuw opbouwen. | [IMPL] |
| SO-052 | Herberekening op blur/change, niet op elke toetsaanslag. | [IMPL] |
| SO-053 | Instrumentsuggesties tonen: [TYPE] Naam | ID: x | ISIN: y | Positie: z. | [IMPL] |

---

## 6. Instrumenten (`/instruments`)

### 6.1 Doel
Beheer van instrumenten (aandelen, obligaties).

### 6.2 Elementen

| Regel | Beschrijving | Status |
|---|---|---|
| SI-001 | Kop: "Instrumenten". | [IMPL] |
| SI-002 | Knop "Nieuw instrument toevoegen" rechtsboven. | [IMPL] |
| SI-003 | Toggle-checkbox "Toon inactieve instrumenten" met directe verversing bij aan/uit. | [IMPL] |
| SI-004 | Tabel met kolommen: Nr, ISIN, Omschrijving, Type, Valuta, Status, Actie. | [IMPL] |
| SI-005 | Geen aparte kolom Naam naast Omschrijving (dezelfde inhoud; één kolom volstaat). | [IMPL] |
| SI-006 | Type: vertaald via `translate_instrument_type` (Aandeel, Obligatie, Optie, Fonds). | [IMPL] |
| SI-007 | Status: "Actief" of "Inactief". | [IMPL] |
| SI-008 | Actieknop "Wijzig" als compacte knop (`.button-sm`). | [IMPL] |
| SI-009 | Succes-/foutmeldingen bovenaan de pagina als banners. | [IMPL] |
| SI-010 | Instrumenten gesorteerd op omschrijving (alfabetisch). | [IMPL] |
| SI-011 | Toggle-formulier behoudt client_id en portfolio_id als hidden fields. | [IMPL] |

### 6.3 Nieuw instrument (`/instruments/new`)

| Regel | Beschrijving | Status |
|---|---|---|
| SI-020 | Stap 1: kies instrumenttype (Bond of Stock). | [IMPL] |
| SI-021 | Stap 2: formulier met velden afhankelijk van gekozen type. | [IMPL] |
| SI-022 | Bond-specifieke velden: einddatum, couponrente, couponfrequentie. | [IMPL] |
| SI-023 | Bij dubbel instrument-ID: foutmelding "Instrument ID bestaat al". | [IMPL] |

### 6.4 Wijzig instrument (`/instruments/edit/<id>`)

| Regel | Beschrijving | Status |
|---|---|---|
| SI-030 | Formulier prefilled met bestaande waarden. | [IMPL] |
| SI-031 | Instrument-ID is niet wijzigbaar. | [IMPL] |
| SI-032 | Bij niet-bestaand ID: HTTP 404 met melding. | [IMPL] |
| SI-033 | Wijzigingen worden opgeslagen in SQLite. | [IMPL] |

---

## 7. Order Drafts (`/order-drafts`)

### 7.1 Doel
Monitoring en opschoning van conceptorders.

### 7.2 Elementen

| Regel | Beschrijving | Status |
|---|---|---|
| SD-001 | Kop: "Order Draft Monitoring". | [IMPL] |
| SD-002 | Context-grid toont: startup cleanup (aantal verwijderd) en retention policy (dagen). | [IMPL] |
| SD-003 | Opschoningsformulier met retentieparameter en bevestigingscheckbox. | [IMPL] |
| SD-004 | Statusoverzichtstabel: Status, Aantal. | [IMPL] |
| SD-005 | Recente conceptorderstabel: Draft ID, Status, Portfolio, Template, Instrument, Actor, Updated. | [IMPL] |
| SD-006 | Actor kolom toont: actor_id + actor_role (indien aanwezig) + actor_channel. | [IMPL] |
| SD-007 | Succesmelding na opschoning met aantal verwijderde records. | [IMPL] |
| SD-008 | Foutmelding als bevestigingcheckbox niet is aangevinkt. | [IMPL] |
