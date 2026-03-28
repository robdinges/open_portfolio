# Order Entry Specificatie

Datum: 2026-03-26
Status: Normatieve functionele specificatie voor orderinvoer

## Doel en scope

Deze specificatie beschrijft de volledige orderinvoerflow voor transacties in OpenPortfolio.
De scope omvat UI-flow, validaties, berekeningen, rekeningselectie en navigatie-uitkomsten.

## Instrumenttypes

Het orderscherm maakt expliciet onderscheid tussen:
- obligaties (`bond`)
- aandelen (`stock`)
- opties (`option`)
- funds (`fund`)

## Standaard workflow voor alle instrumenten

1. Bepaal portefeuillecontext impliciet of expliciet.
2. Kies instrument via zoekbare dropdown, of prefill vanuit holdings-overzicht.
3. Controleer positie in portefeuille en toon huidige hoeveelheid:
- stuks voor aandelen, opties en funds
- nominale waarde voor obligaties
4. Kies transactiesoort: `BUY` of `SELL`.
5. Kies ordertype: `MARKET` of `LIMIT`.
6. Voer orderhoeveelheid in.
7. Valideer orderhoeveelheid op:
- handelseenheid (`smallest_trading_unit`)
- minimale ordergrootte (`minimum_purchase_value`)
8. Toon transactiekosten, eventuele opgelopen rente en ordertotaal.
9. Kies akkoord of annuleren.

## Veldregels per instrumenttype

### Hoeveelheidsveld

- Obligatie:
- invoer = nominale waarde
- label toont instrumentvaluta achter veld
- Aandeel:
- invoer = aantal stuks
- geen valutalabel achter veld
- Optie/Fund:
- invoer = aantal contracten of participaties (conform productconfiguratie)
- geen verplicht valutalabel bij hoeveelheid

### Limietveld

- Obligatie + `LIMIT`:
- invoer als percentage, bijvoorbeeld `100,23`
- interpretatie als `100,23%`
- `%`-teken achter invoerveld
- Aandeel + `LIMIT`:
- invoer als prijs
- instrumentvaluta achter invoerveld
- Optie/Fund + `LIMIT`:
- default: invoer als prijs in instrumentvaluta
- productconfiguratie mag dit overschrijven met expliciet percentagegedrag

### Marktorder

- Bij `MARKET` wordt geen limietprijs gevraagd.
- Koersbepaling gebruikt meest recente instrumentkoers op of voor transactiedatum.

## Rekeningselectie en valuta

1. Bepaal instrumentvaluta en portefeuillevaluta.
2. Als instrumentvaluta gelijk is aan portefeuillevaluta:
- selecteer automatisch de rekening in portefeuillevaluta
- wijziging door gebruiker is niet toegestaan
3. Als instrumentvaluta afwijkt van portefeuillevaluta:
- controleer of instrumentvalutarekening in portefeuille bestaat
- gebruiker mag kiezen uit:
  - instrumentvalutarekening (indien aanwezig)
  - portefeuillevalutarekening
- andere valutarekeningen zijn niet toegestaan
4. Bij elke toegestane rekening toont UI het actuele beschikbare saldo.

## Berekeningen

### Opgelopen rente (obligaties)

- Na invoer van benodigde velden wordt meeverkochte of meegekochte rente berekend en getoond.

### Transactiekosten

- Voor elke order worden transactiekosten berekend via de standaardmethode van de transactiemotor.

### Totaalbedrag

- Voor elke order wordt het totaalbedrag per valuta berekend en getoond.
- Bij valutaomrekening geldt:
- gebruik meest recente FX-koers op of voor transactiedatum
- gebruik reverse FX als directe koers ontbreekt

## Input parsing

- Decimale waarden accepteren zowel komma als punt als decimaalteken.
- Voorbeeld:
- `100,23` en `100.23` worden beide als 100.23 geïnterpreteerd.

## Dynamisch resetgedrag

### Bij wijziging instrument

- Alle afhankelijke velden na instrumentkeuze worden geschoond.
- Velden worden opnieuw conditioneel getoond op basis van het nieuwe instrumenttype.

### Bij wijziging transactiesoort

- Alle afhankelijke velden na transactiesoort worden geschoond.
- Velden worden opnieuw conditioneel getoond op basis van nieuwe transactiesoort.

## Uitkomstacties

- Akkoord:
- transactie wordt vastgelegd
- gebruiker navigeert naar transactiescherm
- Annuleren:
- formulier wordt geschoond
- gebruiker navigeert naar vorige scherm

## Implementatie-aanwijzingen

- Houd routehandlers dun; verplaats herbruikbare orderlogica naar domeinlaag.
- Gebruik altijd enum-gedrag en bestaand productcontract voor validaties.
- Valideer preventief in UI en definitief in transactiemotor.

## Relatie met andere documenten

- Samenvattende requirements staan in `REQUIREMENTS.md` (FR-21 t/m FR-26).
- Always-on UI gedragsregels staan in `.github/instructions.md`.
- Implementatieworkflows staan in skills:
- `.github/skills/transaction-engine/SKILL.md`
- `.github/skills/product-and-instrument-model/SKILL.md`
- `.github/skills/pricing-and-valuation/SKILL.md`
