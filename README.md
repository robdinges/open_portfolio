# OpenPortfolio

OpenPortfolio is een modulaire Python-bibliotheek voor het beheren van beleggingsportefeuilles, met ondersteuning voor meerdere valuta, transactietemplates, rapportages, een desktop- en webinterface, en een realistische demo dataset.

## Inhoud

- [Snel starten](#snel-starten)
- [Belangrijkste features](#belangrijkste-features)
- [Datastructuur & objectmodel](#datastructuur--objectmodel)
- [Voorbeeld: Realistische dataset](#voorbeeld-realistische-dataset)
- [Testen & kwaliteit](#testen--kwaliteit)
- [User interfaces](#user-interfaces)
- [To do](#to-do)

---

## Snel starten

1. **Installeer afhankelijkheden:**
	```bash
	pip install -r requirements.txt
	```

2. **Test de installatie:**
	```bash
	./run_tests.sh
	```

3. **Start de desktop GUI:**
	```bash
	PYTHONPATH=src .venv/bin/python3 -m open_portfolio.gui
	```

4. **Start de webinterface:**
	```bash
	PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
	```

Zie `GETTING_STARTED.md` voor meer details.

---

## Belangrijkste features

- **Modulair & uitbreidbaar:** Accounts, producten, transacties, pricing, analytics, GUI, database.
- **Meerdere interfaces:** Tkinter desktop GUI, Flask web UI.
- **Demo data generator:** Realistische datasets voor testen en demo’s.
- **Transactietemplates:** BUY, SELL, DEPOSIT, DIVIDEND.
- **Multi-valuta:** EUR, USD, met automatische FX-conversie.
- **Producten:** Aandelen en obligaties, incl. rente-opbouw en aflossing.
- **Rapportage:** Overzicht, holdings, transacties, kaspositie.
- **Database:** SQLite persistence voor clients en portefeuilles.
- **Testen:** Uitgebreide pytest suite.

Zie `FEATURES.md` voor een volledig overzicht.

---

## Datastructuur & objectmodel

- **Client** → Portefeuilles → CashAccounts & SecuritiesAccount
- **ProductCollection** → Producten (Stock, Bond)
- **TransactionManager** → Transacties
- **CurrencyPrices** → Valutakoersen

Zie `FEATURES.md` voor een diagram en details.

---

## Voorbeeld: Realistische dataset

De functie `create_realistic_dataset()` (zie `sample_data.py`) maakt een volledige demo-omgeving aan met:
- 2 clients (Alice Johnson, Bob Smith)
- 3 portefeuilles (EUR/USD)
- 8 producten (5 aandelen, 3 obligaties)
- 10 voorbeeldtransacties
- Realistische prijzen en FX-rates

Zie `DATASET_AND_REPORTING.md` voor details en rapportagevoorbeelden.

---

## Testen & kwaliteit

- Alle kernmodules zijn afgedekt met pytest.
- Gebruik `./run_tests.sh` voor consistente testuitvoering.
- Testcases dekken transacties, rapportages, webinterface en meer.

---

## User interfaces

- **Desktop GUI:** Tkinter, direct te starten.
- **Web UI:** Flask, toont overzicht en transacties.
- **Notebook & script:** Zie `src/portfolio_sim.ipynb` en `src/portfolio_sim.py` voor een hands-on demo.

---

## To do

Zie het README-bestand voor een actuele lijst met openstaande verbeteringen en ideeën.

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
