# REQ-02 — Weergave: layout, veldbreedte, uitlijning, navigatie

Datum: 2026-04-06
Bron: `.github/instructions.md`, `base.html`, chatinstructies, huidige implementatie

---

## 1. Paginastructuur en navigatie

| Regel | Beschrijving | Status |
|---|---|---|
| WL-001 | Elke pagina bevat een vaste header met applicatienaam en navigatiebalk. | [IMPL] |
| WL-002 | Navigatiebalk bevat links naar: Home, Cash Accounts, Holdings, Transactions, Order Drafts, Instruments. | [IMPL] |
| WL-003 | Actieve pagina wordt visueel gemarkeerd in de navigatiebalk (`.active` class). | [IMPL] |
| WL-004 | Navigatielinks behouden de huidige client- en portfolio-context via `nav_query` queryparameters. | [IMPL] |
| WL-005 | Niet-home pagina's tonen een "Naar Home" knop rechtsboven. | [IMPL] |
| WL-006 | Home is het centrale startpunt: eerst client selecteren, daarna dynamisch portefeuilleoverzicht. | [IMPL] |

## 2. Context-header (context-grid)

| Regel | Beschrijving | Status |
|---|---|---|
| WL-010 | Schermen met portfolio-context tonen een context-grid bovenaan met: Klant, Portefeuille, Portefeuille-id. | [IMPL] |
| WL-011 | Volgorde in context-grid: eerst Klant, dan Portefeuille, dan Portefeuille-id. | [IMPL] |
| WL-012 | Context-grid gebruikt een 2-koloms layout: label (140–220px) + waarde (rest). | [IMPL] |
| WL-013 | Labels zijn vetgedrukt (font-weight 700). | [IMPL] |

## 3. Tabelopmaak

| Regel | Beschrijving | Status |
|---|---|---|
| WL-020 | Tabellen vullen de volledige breedte van het inhoudsgebied. | [IMPL] |
| WL-021 | Kolomkoppen worden in hoofdletters weergegeven, verkleind lettertype (0.92rem), vetgedrukt, grijze achtergrond (`#edf3f8`). | [IMPL] |
| WL-022 | Tabelinhoud heeft een lichte achtergrond (75% doorzichtig wit) met afgeronde hoeken. | [IMPL] |
| WL-023 | Celpadding: 0.8rem verticaal, 0.9rem horizontaal. | [IMPL] |
| WL-024 | Rijscheidingslijnen: 1px lijn in lichtgrijs (`#ebf0f4`). | [IMPL] |

## 4. Bedraguitlijning

| Regel | Beschrijving | Status |
|---|---|---|
| WL-030 | Kolommen met bedragen en prijzen worden rechts uitgelijnd (class `valuta`). | [IMPL] |
| WL-031 | Bedragkolommen gebruiken monospace numerieke tekens (`font-variant-numeric: tabular-nums`). | [IMPL] |
| WL-032 | Minimale breedte voor bedragkolommen: 7em. | [IMPL] |
| WL-033 | Bedragen visueel uitlijnen op de decimale komma (impliciet door rechtsuitlijning + vaste decimalen). | [IMPL] |

## 5. Knoppen

| Regel | Beschrijving | Status |
|---|---|---|
| WL-040 | Standaardknop (`.button`): blauwe gradiënt, afgeronde hoeken (999px radius), minimale hoogte 2.85rem, schaduw. | [IMPL] |
| WL-041 | Annuleerknop (`.button.cancel`): grijze gradiënt, donkere tekst. | [IMPL] |
| WL-042 | Compacte knop (`.button-sm`): kleinere variant voor actieknoppen in tabellen. Hoogte 1.8rem, padding 0.3rem 0.7rem, lettergrootte 0.82rem. | [IMPL] |
| WL-043 | In data-grids (holdings, instrumenten) worden compacte knoppen (`.button-sm`) gebruikt voor rij-acties. | [IMPL] |
| WL-044 | Paginaniveau-acties (Nieuw instrument, Nieuwe transactie) gebruiken standaardknoppen. | [IMPL] |

## 6. Invoervelden

| Regel | Beschrijving | Status |
|---|---|---|
| WL-050 | Invoervelden krijgen een realistische breedte, passend bij de verwachte waarde. Niet standaard full-width. | [SPEC] |
| WL-051 | Formulieren gebruiken een 2-koloms grid-layout: label links (150–220px), veld rechts (max 32rem). | [IMPL] |
| WL-052 | Actieve invoervelden tonen een blauwe focusrand met lichte schaduw. | [IMPL] |
| WL-053 | Invoervelden hebben afgeronde hoeken (12px radius) en lichte rand. | [IMPL] |
| WL-054 | Gebruik duidelijke placeholders die het verwachte formaat aangeven. | [SPEC] |

## 7. Formulieracties

| Regel | Beschrijving | Status |
|---|---|---|
| WL-060 | Actieknoppen in formulieren staan in een horizontale rij met 0.85rem tussenruimte. | [IMPL] |
| WL-061 | Top-actions (rechtsboven pagina) gebruiken flex layout met `justify-content: flex-end`. | [IMPL] |

## 8. Foutmeldingen en succesberichten

| Regel | Beschrijving | Status |
|---|---|---|
| WL-070 | Foutmeldingen: rode tekst, licht rode achtergrond, rode rand, vetgedrukt. | [IMPL] |
| WL-071 | Succesberichten: groene tekst, licht groene achtergrond, groene rand, vetgedrukt. | [IMPL] |
| WL-072 | Meldingen worden bovenaan het relevante inhoudsblok getoond, voor de tabel of het formulier. | [IMPL] |
| WL-073 | Veldspecifieke fouten moeten bij het relevante veld worden getoond. | [SPEC] |

## 9. Responsiviteit

| Regel | Beschrijving | Status |
|---|---|---|
| WL-080 | Hoofdinhoud is gecentreerd met maximale breedte 1440px en 20px marge aan weerszijden. | [IMPL] |
| WL-081 | Op schermen smaller dan 860px schakelt formulierlayout over naar 1 kolom. | [IMPL] |
| WL-082 | Tabellen en invoervelden passen zich aan aan schermgrootte. | [SPEC] |

## 10. Kleurgebruik en consistentie

| Regel | Beschrijving | Status |
|---|---|---|
| WL-090 | Primaire kleur: donkergroen (`#166534`). | [IMPL] |
| WL-091 | Header: donkerblauw gradiënt. | [IMPL] |
| WL-092 | Knoppen: blauw gradiënt. | [IMPL] |
| WL-093 | Gelijke functies en gelijke velden gebruiken een uniforme en herkenbare kleur. | [SPEC] |
| WL-094 | Achtergrond: subtiele gradiënt van lichtblauw naar lichtgeel met groene en oranje accenten. | [IMPL] |
