# REQ-01 — Weergave: data in velden, teksten, afronding

Datum: 2026-04-06
Bron: `.github/instructions.md`, chatinstructies, huidige implementatie

---

## 1. Valutabedragen

| Regel | Beschrijving | Status |
|---|---|---|
| WD-001 | Bedragen altijd in 2 decimalen tonen. | [IMPL] |
| WD-002 | Decimaalteken is de komma (`,`). Duizendtalseparator is de punt (`.`). Voorbeeld: `1.234,56`. | [IMPL] |
| WD-003 | Valutacode (ISO 4217) staat **achter** het bedrag. Voorbeeld: `1.234,56 EUR`. | [IMPL] |
| WD-004 | Interne berekeningen mogen met hogere precisie plaatsvinden; presentatie blijft 2 decimalen. | [SPEC] |
| WD-005 | Half-up afronding voor monetaire waarden naar valutaprecisie. | [SPEC] |

## 2. Aantallen en hoeveelheden

| Regel | Beschrijving | Status |
|---|---|---|
| WD-010 | Hele aantallen tonen als geheel getal, zonder decimalen. Voorbeeld: `100`. | [IMPL] |
| WD-011 | Aantallen met decimalen: toon 2 decimalen met dezelfde duizendtalseparator als bedragen. Voorbeeld: `1.234,56`. | [IMPL] |
| WD-012 | Geen suffix "stuks" bij aantallen; alleen het getal. | [IMPL] |
| WD-013 | Bij obligaties: nominale waarde gevolgd door instrumentvaluta. Voorbeeld: `10.000 EUR`. | [IMPL] |

## 3. Percentages

| Regel | Beschrijving | Status |
|---|---|---|
| WD-020 | Obligatiekoersen worden weergegeven als percentage met `%`-teken erachter. Voorbeeld: `101,25%`. | [IMPL] |
| WD-021 | Obligatie-limietprijzen bij LIMIT-orders: invoer als percentage, teken `%` achter het invoerveld. | [IMPL] |
| WD-022 | Percentages standaard op 2 decimalen, tenzij meer precisie vereist is voor berekening. | [IMPL] |

## 4. Datumweergave

| Regel | Beschrijving | Status |
|---|---|---|
| WD-030 | Datums in het transactieformulier worden getoond als `dd-mm-yyyy`. | [IMPL] |
| WD-031 | Datums in transactie-overzichten worden getoond als ISO-formaat `yyyy-mm-dd`. | [IMPL] |
| WD-032 | Timestamps in concept-orderoverzicht worden getoond als ruwe datetime. | [IMPL] |

## 5. Codes en identificatie

| Regel | Beschrijving | Status |
|---|---|---|
| WD-040 | Toon altijd een code (id) samen met een korte omschrijving. Voorbeeld: `12345 – Pensioenfonds XYZ`. | [SPEC] |
| WD-041 | Gebruik interne unieke ID's voor instrumenten en portefeuilles. Vermijd hardcoded namen. | [SPEC] |

## 6. Vertaling van types en termen

### 6a. Transactietypes (movementtypes)

| Interne waarde | Weergavetekst | Status |
|---|---|---|
| `security_buy` | Aankoop | [IMPL] |
| `security_sell` | Verkoop | [IMPL] |
| `deposit` | Storting | [IMPL] |
| `withdrawal` | Opname | [IMPL] |
| `dividend` | Dividend | [IMPL] |
| `costs` | Kosten | [IMPL] |
| `accrued_interest` | Opgelopen rente | [IMPL] |

### 6b. Instrumenttypes

| Interne waarde | Weergavetekst | Status |
|---|---|---|
| `STOCK` / `Stock` | Aandeel | [IMPL] |
| `BOND` / `Bond` | Obligatie | [IMPL] |
| `OPTION` | Optie | [IMPL] |
| `FUND` | Fonds | [IMPL] |

### 6c. Accounttypes

| Interne waarde | Weergavetekst | Status |
|---|---|---|
| `CASH` | Kas | [IMPLICIET] |
| `SAVINGS` | Spaar | [IMPLICIET] |
| `SECURITIES` | Effecten | [IMPLICIET] |

## 7. Invoerparsing

| Regel | Beschrijving | Status |
|---|---|---|
| WD-070 | Decimale waarden accepteren zowel komma als punt als decimaalteken. `100,23` en `100.23` worden beide als 100.23 geïnterpreteerd. | [IMPL] |
| WD-071 | Spaties in numerieke invoer worden genegeerd. | [IMPL] |

## 8. Lege of ontbrekende waarden

| Regel | Beschrijving | Status |
|---|---|---|
| WD-080 | Ontbrekende waarden in overzichtstabellen worden getoond als `-`. | [IMPL] |
| WD-081 | Afgeleide velden (brutobedrag, kosten, totaal) tonen `-` als nog niet berekend. | [IMPL] |
| WD-082 | ISIN toont `-` als het veld leeg is. | [IMPL] |

## 9. Statusweergave

| Regel | Beschrijving | Status |
|---|---|---|
| WD-090 | Instrument actief/inactief wordt weergegeven als `Actief` / `Inactief`. | [IMPL] |
| WD-091 | Orderstatus wordt in hoofdletters getoond (DRAFT, VALIDATED, REJECTED, SUBMITTED). | [IMPL] |
| WD-092 | Bij een nieuwe order zonder draft-id wordt status getoond als `Nieuw`. | [IMPL] |
