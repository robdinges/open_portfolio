# Project Skills & Best Practices

## UI-generatie & Consistentie
- Detecteer en corrigeer inconsistenties in filtering, zoals ontbrekende of niet-geselecteerde clients/portefeuilles.
- Voorkom dubbele of conflicterende invoervelden; elk veld mag slechts één keer en op logische plek voorkomen.
- Zorg dat gebruikerscontext (client, portfolio, portfolio-id) altijd correct en eenduidig wordt doorgegeven aan alle schermen, routes en API-calls.
- Valideer dat alle dropdowns en selecties dynamisch gevuld worden op basis van de actuele context.

## Transactie-intelligentie
- Bepaal automatisch de juiste cashrekening op basis van instrumentvaluta en portfolio base currency.
- Bereken en toon altijd een kosteninschatting en het totaalbedrag inclusief fees en belastingen vóór bevestiging.
- Implementeer valuta-logica:
  - Altijd tegenvaluta = portfolio base currency.
  - Voorkom onnodige FX-transacties (EUR→EUR = 1).
  - Toon altijd de juiste valutacode of -symbool per rekening en transactie.

## Foutdetectie & Robuustheid
- Herken en los typische UI-bugs structureel op:
  - Ontbrekende of foutieve data in dropdowns/selecties.
  - Verkeerde valuta-symbolen of onjuiste bedragen.
  - HTTP-fouten zoals “Method Not Allowed” door verkeerde methodes in forms/routing.
- Implementeer centrale validatie en error-handling voor forms, routes en API’s.

## Prefill & Context-aware gedrag
- Bij navigatie vanuit holdings of andere contextschermen:
  - Vul instrument, client en portfolio automatisch in op het transactiescherm.
  - Houd gebruikerscontext persistent tussen schermen (bijv. via session of state).
- Zorg dat na een transactie de relevante context behouden blijft voor vervolgacties.

---

### Optioneel (aanbevolen)
- Definieer standaard end-to-end testscenario’s voor alle belangrijke gebruikersflows (bijv. client selecteren → transactie uitvoeren → holdings controleren).
- Log relevante user-acties en systeemgebeurtenissen voor debugging, validatie en audit.
- Hanteer consistente en duidelijke naamgeving voor routes, templates en componenten.
- Gebruik herbruikbare UI-componenten/partials (zoals een context-header) voor maximale consistentie en onderhoudbaarheid.
