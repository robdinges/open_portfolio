# OpenPortfolio

OpenPortfolio is een modulaire Python-bibliotheek voor het beheren van
beleggingsportefeuilles, met ondersteuning voor meerdere valuta,
transactietemplates, orderinvoer, instrumentbeheer, rapportages, een
webinterface en een realistische demo-dataset.

## Inhoud

- [Snel starten](#snel-starten)
- [Belangrijkste features](#belangrijkste-features)
- [Datastructuur & objectmodel](#datastructuur--objectmodel)
- [Voorbeeld: Realistische dataset](#voorbeeld-realistische-dataset)
- [Testen & kwaliteit](#testen--kwaliteit)
- [Webinterface](#webinterface)

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

3. **Start de webinterface:**
   ```bash
   PYTHONPATH=src .venv/bin/python3 -m open_portfolio.web_app
   ```

   Open vervolgens `http://127.0.0.1:5000/` in de browser.

Zie [GETTING_STARTED.md](GETTING_STARTED.md) voor meer details.

---

## Belangrijkste features

- **Modulair & uitbreidbaar:** Accounts, producten, transacties, pricing,
  analytics, rapportage, database.
- **Webinterface (Flask):** Dashboard, holdings, transacties, orderinvoer,
  instrumentbeheer, order-draft monitoring.
- **Orderinvoer:** Volledig transactieformulier met BUY/SELL, MARKET/LIMIT,
  instrumentzoeker, draft/validate/submit-workflow, kostencalculatie en
  opgelopen rente voor obligaties.
- **Instrumentbeheer:** Aandelen, obligaties, opties en fondsen toevoegen en
  bewerken via web-UI; persistentie in SQLite.
- **Order-draft lifecycle:** Conceptorders met status
  (DRAFT/VALIDATED/REJECTED/SUBMITTED) en retentiebeleid.
- **Demo data generator:** Realistische datasets voor testen en demo's.
- **Transactietemplates:** BUY, SELL, DEPOSIT, DIVIDEND.
- **Multi-valuta:** EUR, USD, GBP, CHF, NOK met automatische FX-conversie.
- **Producten:** Aandelen, obligaties, opties en fondsen, incl. rente-opbouw
  en aflossing voor obligaties.
- **Rapportage:** Overzicht, holdings, transacties, kaspositie
  (console, tekst en markdown).
- **Database:** SQLite-persistentie voor clients, portefeuilles, conceptorders
  en instrumenten.
- **Testen:** Uitgebreide pytest-suite (49 tests).

Zie [FEATURES.md](FEATURES.md) voor een volledig overzicht.

---

## Datastructuur & objectmodel

- **Client** → Portefeuilles → CashAccounts & SecuritiesAccount
- **ProductCollection** → Producten (Stock, Bond, Option, Fund)
- **TransactionManager** → Transacties (BUY, SELL, DEPOSIT, DIVIDEND)
- **OrderDraft** → Conceptorders met status en validatie
- **CurrencyPrices** → Valutakoersen en productprijzen
- **Database** → SQLite-tabellen voor clients, portefeuilles, orders,
  instrumenten

Zie [FEATURES.md](FEATURES.md) voor een diagram en details.

---

## Voorbeeld: Realistische dataset

De functie `create_realistic_dataset()` (zie `sample_data.py`) maakt een
volledige demo-omgeving aan met:

- 2 clients (Alice Johnson, Bob Smith)
- 3 portefeuilles (EUR/USD)
- 27 producten (5 aandelen, 22 obligaties)
- 10 voorbeeldtransacties
- Realistische prijzen en FX-rates

Zie [DATASET_AND_REPORTING.md](DATASET_AND_REPORTING.md) voor details en
rapportagevoorbeelden.

---

## Testen & kwaliteit

- **49 tests** verdeeld over 5 testbestanden.
- Alle kernmodules zijn afgedekt met pytest.
- Gebruik `./run_tests.sh` voor consistente testuitvoering.
- Testcases dekken transacties, rapportages, database, webinterface,
  orderinvoer, instrumentbeheer en GUI-scenario's.

---

## Webinterface

- **Dashboard:** Client- en portefeuilleselectie met samenvattende
  statistieken.
- **Holdings:** Effecten- en kasposities per portefeuille.
- **Transacties:** Transactieoverzicht, gesorteerd op datum.
- **Orderinvoer:** Formulier met instrumentzoeker, positie-indicator,
  kosten/rente-preview en draft-workflow.
- **Instrumentbeheer:** Toevoegen, bewerken en activeren/deactiveren van
  instrumenten.
- **Order-drafts:** Monitoringpagina met statusverdeling en opschoning.
- **Rekeningen:** Kasrekeningenoverzicht per portefeuille.
- **Notebook & script:** Zie `src/portfolio_sim.ipynb` en
  `src/portfolio_sim.py` voor een hands-on demo.
