# OpenPortfolio

## To do

- kosten berekenen
- spaarrente berekenen
- vervangen n/a door waarschuwing: geen valuta
- controle of een instrument klopt bij opvoer:

- inlezen producten
- inlezen transacties
- inlezen koersen
- overal hulptekst toevoegen
- overal logging toevoegen
- indeling in classes laten reviewen

- user interface
- api
- database gebruiken

## findings:
 - origineel amount en amount omgedraaid
 - transacties met kosten wordt wel uitgevoerd
 - USD rekening niet gevonden, niet naar EUR

## test cases

### aankoop USD aandeel

- met USD-rekening: wordt automatisch alles in USD geboekt (ook kosten)
- met alleen EUR-rekening: alles wordt omgerekend naar EUR
- bij omrekening juiste valutakoers (laatst bekende) gebruiken en deze vastleggen bij transactie

### transactie met opgelopen rente

- juiste berekening van de opgelopen rente, ook met meerdere YEAR, END_DATE, ACT_ACT, THIRTY_360
- aparte boekingsregel

### kostenberekening

- juiste berekening indien niet opgegeven
- juiste overname opgegeven bedrag
- boeken in juiste valuta, met juiste teken (+/-)

### buying power

- altijd bepalen tov de rekening waarop wordt afgerekend
- afwijzen bij onvoldoende saldo
- ook afwijzen als het eerste deel juist is (bijv wel voldoende voor aankoop, niet meer voor kosten)
- stukken controleren bij verkoop
- bij verwerking transactie: alles of niets

### aanmaken rekening

- controleren of een rekening van hetzelfde type en in zelfde valuta al bestaat
- standaard de automatisch geopende rekening gebruiken
- rekeningen krijgen altijd hetzelfde nummmer als de portfolio, niet zelf te kiezen

### ordercontroles

- rekening houden met min transactie-aantal en unit, ook voor fracties
- rekening houde met start en einddatum van producten
- controleer of alles bestaat: portfolio, product etc

### holdings

- holding per valutadatum kloppend
- juiste berekening rendement holding en portfolio
- juiste vermelding opgelopen rente
- gemiddelde aankoopprijs
- obligaties: ytm, duration

## kalender
Ptf 10, rek EUR, 15.000
Ptf 10, rek USD, 5.000
Ptf 10, rek GBP, 1.000
Ptf 20, rek EUR, 10.000

Koersen USD-EUR: ... voor alle data en maandultimo

bond1: 01-01-2024 - 31-12-2024, EUR, 5%, ACT_ACT, YEAR
bond2: 01-11-2022 - 31-10-2032, USD, 3%, 30_360, YEAR
bond3: 01-01-2020 - 31-12-2025, EUR, 4%, ACT_ACT, END_DATE
stock1: GBP,
stock2: (fund), EUR, 0.001,

koersen bond1, bond2, bond3, stock1, stock2 voor alle data en maandultimo

jan 2024
 - 30-01-2024: aankoop bond1 via EUR-rekening 10: 5000

feb 2024
 - 15-02-2024: aankoop stock1 via GBP-rekening 10: 10 @ 100 --> alleen aankoop past in buying power
 - 20-02-2024: aankoop stock2 via EUR-rekening 10: 1.2345 @ 20 --> afwijzing
 - 25-02-2024: aankoop stock2 via EUR-rekening 10: 1.234 @ 20 --> akkoord 
 - 28-02-2024: aankoop bond3 via EUR-rekening 10: 1000 --> opgelopen rente vanaf start

mrt 2024
 - 15-03-2024: aankoop stock1 via GBP-rekening 10: 5 @ 100 --> geaccepteerd
 - 31-03-2024: aankoop bond2 via USD-rekening 10: 2000 --> opgelopen rente 30 apr, alles in USD
 - 31-03-2024: aankoop bond2 via EUR-rekening 20: 4000 --> opgelopen rente 30 apr, alles in EUR

apr 2024
 - 15-04-2024: verkoop stock1 via GBP-rekening 10: 6 @ 110 --> afwijzing wegens onvoldoende stukken
 - 20-04-2024: verkoop stock1 via GBP-rekening 10: 4 @ 110 --> akkoord
 - 30-04-2024: verkoop bond2 via USD-rekening 10: 1000 --> alles in USD
 - 31-03-2024: verkoop bond2 via EUR-rekening 20: 2000 --> alles in EUR

jan 2025
 - 15-01-2025: aankoop bond1 via EUR-rekening 10: 1000 --> afwijzing vanwege einddatum
