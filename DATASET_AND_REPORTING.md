# OpenPortfolio: Dataset & Reporting

## Overzicht

Dit document beschrijft de demo-dataset en rapportagemogelijkheden van
OpenPortfolio.

## Dataset (`src/open_portfolio/sample_data.py`)

### Functie: `create_realistic_dataset()`

Genereert een complete, realistische multi-portfolio dataset voor testen
en demo's. Alle data wordt geladen vanuit `data/*.json`.

### Dataset-inhoud

**Clients (2):**

- Alice Johnson (ID: 1)
- Bob Smith (ID: 2)

**Portefeuilles (3):**

- Portfolio 1: Alice Johnson – Groei Europa (EUR, startkas € 50.000)
- Portfolio 2: Alice Johnson – Tech Amerika (USD, startkas $ 30.000)
- Portfolio 3: Bob Smith – Obligaties NL (EUR, startkas € 75.000)

**Kasrekeningen:**

- Portfolio 1: EUR (50.000), GBP (1.234)
- Portfolio 2: USD (30.000), EUR (10.000)
- Portfolio 3: EUR (75.000)

**Producten (27):**

*Aandelen (5):*

- Apple Inc. (AAPL) – USD
- Microsoft Corp. (MSFT) – USD
- Alphabet Inc. (GOOGL) – USD
- Amazon.com (AMZN) – USD
- ASML Holding (ASML) – EUR

*Basisobligaties (3):*

- EU Government Bond 2.5% – EUR (looptijd 2030)
- Rabobank 2027 – EUR (looptijd 2027)
- US Treasury Bond 4.0% – USD (looptijd 2033)

*Uitgebreide obligaties (19):*

- German, Austrian, French, Irish overheidsobligaties
- Corporate bonds: BMW, Continental, KFW, Mercedes, SAP, Volkswagen, EIB
- Electricité de France, ING Green Bond
- Dutch, Austrian, Spanish overheidsobligaties
- Valuta: EUR, USD, NOK

**Prijzen:**

- Productprijzen geladen vanuit `data/prices.json`
- FX-koersen geladen vanuit `data/currency_prices.json`
  (o.a. USD/EUR, GBP/EUR, NOK/EUR)

**Transacties (10):**

*Alice EUR-portefeuille:*

1. Sept 2025: BUY Siemens/ASML 100 @ €145
2. Okt 2025: BUY EU Bond 10 @ 102
3. Nov 2025: BUY Corporate Bond 8 @ 101,5
4. Dec 2025: BUY Siemens/ASML 50 @ €151

*Alice USD-portefeuille:*

5. Sept 2025: BUY Apple 30 @ $210
6. Okt 2025: BUY Microsoft 15 @ $385
7. Nov 2025: BUY US Bond 2 @ 101

*Bob EUR-portefeuille:*

8. Sept 2025: BUY EU Bond 30 @ 102
9. Okt 2025: BUY Siemens/ASML 200 @ €147
10. Nov 2025: BUY Corporate Bond 20 @ 101,5

### Gebruik

```python
from open_portfolio.sample_data import create_realistic_dataset

dataset = create_realistic_dataset()

clients = dataset['clients']           # List[Client] (2 clients)
portfolios = dataset['portfolios']     # List[Portfolio] (3 portfolios)
products = dataset['products']         # ProductCollection (27 producten)
prices = dataset['prices']             # CurrencyPrices
transactions = dataset['transactions'] # List (uitgevoerde transacties)
```

## Rapportagemodule (`src/open_portfolio/reporting.py`)

### Klasse: `PortfolioReporter`

```python
from open_portfolio.reporting import PortfolioReporter

reporter = PortfolioReporter(clients)
```

### Methoden

**`print_summary(valuation_date=None)`**

Toont portefeuilletotalen per client: kas, effectenwaarde en totaal.

**`print_detailed_holdings(valuation_date=None)`**

Lijst alle kasrekeningen met saldi en effectenposities met actuele
waarde.

**`print_transaction_history()`**

Toont alle transacties in chronologische volgorde per portefeuille.

**`print_cash_position(valuation_date=None)`**

Kaspositie per valuta en rekeningtype.

**`print_all_reports(valuation_date=None)`**

Voert alle 4 rapporten achtereenvolgens uit.

**`to_text(valuation_date=None)`**

Exporteert het volledige rapport als string.

**`to_markdown(valuation_date=None)`**

Genereert een markdown-rapport met portefeuilleoverzicht, holdings-
tabellen en transactiehistorie.

### Voorbeeld

```python
from open_portfolio.sample_data import create_realistic_dataset
from open_portfolio.reporting import PortfolioReporter
from datetime import date

dataset = create_realistic_dataset()
reporter = PortfolioReporter(dataset['clients'])

reporter.print_all_reports(valuation_date=date(2026, 3, 1))

report_text = reporter.to_text(valuation_date=date(2026, 3, 1))
with open('portfolio_report.txt', 'w') as f:
    f.write(report_text)
```

## Analytics (`src/open_portfolio/analytics.py`)

### Klasse: `PortfolioAnalytics`

**`get_holdings_progress(product_id)`**

Retourneert het historisch verloop van een positie: datum, hoeveelheid,
prijs en waarde per tijdstip.

## Testen

### Testbestand: `tests/test_reporting.py`

5 tests valideren de dataset en rapportagefunctionaliteit:

1. **test_realistic_dataset_creation** – Controleert 2 clients,
   3 portefeuilles, 27 producten, ≥10 transacties.
2. **test_portfolio_reporter_summary** – Valideert summary-rapport.
3. **test_portfolio_reporter_holdings** – Controleert kas- en
   effectensecties.
4. **test_portfolio_reporter_transactions** – Controleert
   transactiehistorie.
5. **test_portfolio_reporter_text_export** – Valideert tekstexport.

### Tests uitvoeren

```bash
PYTHONPATH=src .venv/bin/python3 -m pytest tests/test_reporting.py -v

# Of alle tests:
./run_tests.sh
```

## Databestanden

De dataset wordt geladen vanuit JSON-bestanden in de `data/` directory:

| Bestand | Inhoud |
|---|---|
| `clients.json` | 2 clients met id en naam |
| `portfolios.json` | 3 portefeuilles met client-koppeling en valuta |
| `cash_accounts.json` | Kasrekeningen per portefeuille en valuta |
| `products.json` | 27 producten (aandelen + obligaties) |
| `prices.json` | Koershistorie per product |
| `currency_prices.json` | FX-koersen per valutapaar en datum |
| `transactions.json` | 10 voorbeeldtransacties |

## Kenmerken realistische data

- Multi-valuta: EUR, USD, GBP, CHF, NOK
- Realistische koersprogressie met dagelijkse variatie
- Obligatiekoersen in percentages (standaard marktconventie)
- Mix van aandelen en obligaties voor diversificatie
- Meerdere portefeuilles met verschillende strategieën
- Kasrekeningen afgestemd op transactievolumes
- Transacties verspreid over meerdere maanden
