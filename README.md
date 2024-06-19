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


## test cases:

### aankoop USD aandeel:
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