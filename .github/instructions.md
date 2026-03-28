# UI & Data Presentation Instructions

## Valutaweergave
- **Valutaformaat**: Toon bedragen altijd in valutaformaat: valutasymbool of ISO-code, gevolgd door het bedrag met twee decimalen.
- **Decimalen**: Gebruik standaard een decimale komma (`,`) en een punt (`.`) als duizendtalseparator.  
  _Voorbeeld: € 1.234,56 of EUR 1.234,56_
- **Uitlijning**: Lijn bedragen in tabellen en overzichten zoveel mogelijk onder elkaar uit op de decimale komma.
- **Rekenkundige precisie**: Interne berekeningen mogen met meer decimalen plaatsvinden, maar de presentatie blijft op twee decimalen.

## Context bij codes
- **Combinatie van code en omschrijving**: Toon altijd de code (zoals portfolio-id, product-id) samen met een korte omschrijving op webpagina’s en in overzichten, zodat de gebruiker direct context heeft.
  _Voorbeeld: “12345 – Pensioenfonds XYZ”_

## Invoervelden
- **Breedte**: Geef invoervelden een realistische breedte, passend bij de te verwachten waarde. Vul velden niet standaard over de volledige breedte van het scherm.
- **Placeholder**: Gebruik duidelijke placeholders die het verwachte formaat aangeven (bijvoorbeeld “1.234,56”).

## Aanvullende suggesties
- **Responsiveness**: Zorg dat tabellen en invoervelden zich aanpassen aan verschillende schermgroottes.
- **Toegankelijkheid**: Gebruik toegankelijke labels en aria-attributes waar mogelijk.
- **Foutmeldingen**: Geef duidelijke, gebruikersvriendelijke foutmeldingen bij ongeldige invoer.
- **Consistentie**: Gebruik overal dezelfde formattering voor bedragen en codes.
- **Sorting**: Sta sorteren toe op kolommen met bedragen en codes.
- **Tooltip**: Overweeg tooltips voor afkortingen of codes voor extra uitleg.


## UI & Navigatie
- Elke pagina bevat consistente navigatie (menu + terugknop naar Home).
- Home is centrale entry: eerst client selecteren, daarna dynamisch gefilterde portefeuilles tonen.
- Geselecteerde portfolio is globale context voor alle schermen (holdings, transacties, cash accounts).
- Context (client, portfolio, portfolio id) altijd zichtbaar bovenaan elk relevant scherm.

## Data filtering & consistentie
- Alle schermen tonen data gefilterd op geselecteerde client/portfolio.
- Geen hardcoded of default selectie (bijv. alleen client1); altijd dynamisch laden.
- Verwijder redundante schermen als functionaliteit al in andere UI zit (bijv. Clients/Portfolios geïntegreerd in Home).

## Valuta & bedragen (uitbreiding)
- Bedragen altijd in valutaformaat:
  - 2 decimalen
  - decimale komma, punt als duizendtalseparator
- Berekeningen intern met hogere precisie toegestaan.
- Bedragen visueel uitlijnen op decimale komma.
- Toon altijd valuta (ISO of symbool) correct per rekening.

## Formulieren & interactie
- Bij verlaten pagina met wijzigingen:
  - expliciet save of discard afdwingen
- Invoervelden:
  - logisch uitgelijnd (label + veld)
  - realistische breedte (niet full-width)
- Geen dubbele of onduidelijke invoervelden.

## Transactielogica (UI gedrag)
- Flow: client → portfolio → instrument → transactie.
- Dynamische invoer afhankelijk van instrumenttype (bijv. aandelen vs obligaties).
- Default cashrekening:
  - gebaseerd op instrumentvaluta (indien beschikbaar)
- Altijd tonen:
  - huidig saldo
  - saldo na transactie
  - totaal af te boeken bedrag
- Debetsaldo niet toegestaan.
- Alternatieve rekening (portfolio valuta) altijd selecteerbaar.

## Validaties
- Verkoop alleen mogelijk bij voldoende positie.
- UI toont huidige positie bij selectie instrument.
- Fouten voorkomen i.p.v. tonen (preventieve validatie).

## Order Entry & Validatie
- Orderscherm maakt onderscheid tussen instrumenttypes: obligatie, aandeel, optie, fund.
- Workflow blijft gelijk: portefeuille -> instrument -> transactiesoort -> ordertype -> hoeveelheid -> afrekenrekening -> bevestigen/annuleren.
- Instrumentkeuze ondersteunt prefill vanuit holdings en zoekbare selectie.
- Na instrumentkeuze altijd positie tonen (stuks of nominaal).
- Validatie op handelseenheid en minimale ordergrootte gebeurt direct na invoer.
- Invoervelden tonen contextlabels:
  - hoeveelheidseenheid,
  - minimale ordergrootte,
  - valuta of `%` waar van toepassing.
- Rekeningkeuze wordt beperkt tot instrumentvaluta en portefeuillevaluta, met zichtbaar beschikbaar saldo.
- Als instrumentvaluta gelijk is aan portefeuillevaluta is de rekening vast en niet wijzigbaar.
- Voor obligaties opgelopen rente tonen zodra benodigde ordervelden ingevuld zijn.
- Voor elke order transactiekosten en totaalbedrag per valuta tonen.
- Bij wisselkoers of koersgebruik altijd meest recente waarde op of voor transactiedatum gebruiken.
- Decimale invoer accepteert komma en punt.
- Bij wijziging van instrument of transactiesoort afhankelijke velden resetten en conditioneel opnieuw tonen.
- Akkoord navigeert naar transactiescherm; annuleren navigeert terug naar vorige scherm en schoont formulier.
- Normatieve detailregels voor orderinvoer staan in `ORDER_ENTRY.md`.

## Feedback & flow
- Na succesvolle transactie: redirect naar transactiescherm of holdings.
- Vanuit holdings:
  - Buy/Sell knop opent transactie met prefilled context.
- Ingevoerde transacties direct zichtbaar in overzicht.

## Data model & identificatie
- Gebruik interne unieke ID’s voor:
  - instrumenten
  - portefeuilles
- Toon ID + naam samen voor context.
- Vermijd hardcoded namen (zoals “stock_siemens”).

## Architectuur
- Scheid:
  - UI (Flask templates)
  - business logic
  - data (JSON/CSV mogelijk)
- Verwijder redundante code en structureer in logische modules.
- Eén consistente manier voor state management (bijv. session).

## Eenduidigheid
- **Kleurgebruik**: zorg dat gelijke functies en gelijke velden een uniforme en herkenbare kleur

## Onderhoud SKILLS.md en instructions.md
- kijk bij elke prompt die ik je geef of het handig is om op basis daarvan de SKILLS of de instructions aan te vullen of te wijzigen.
