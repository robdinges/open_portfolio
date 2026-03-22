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

## Skill file of instructions?
- **UI/UX-richtlijnen** zoals hierboven beschreven horen thuis in een instructions file.
- **Specifieke formatteringsfuncties** (zoals een Python-functie voor valutaformattering) kun je beter in een skill file of als utility-functie in je codebase opnemen.
