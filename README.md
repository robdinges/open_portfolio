# Bond Workspace

Streamlit-app voor obligatiebeheer met persistente SQLite-opslag, transactiereconciliatie en analyse.

## Huidige indeling

- `app.py`  
  Hoofdapp met schermen: `Transactie-overzicht`, `Obligatie-tijdlijn`, `Koersen`, `Analyse`, `Onderhoud obligaties`.
- `OpenPortfolioLib.py`  
  Portefeuille- en transactiekern.
- `src/bond_suite/`  
  Geconsolideerde package (engine + analytics wrappers).
- `data/portfolio.db`  
  SQLite database (automatisch aangemaakt).

## Installatie

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Gebruik

```bash
streamlit run app.py
```

## Persistente opslag

SQLite in `data/portfolio.db` met tabellen:

- `instruments`
- `accounts`
- `transactions`
- `bond_prices`
- `fx_rates`
- `import_log`

Transactie-import is idempotent via unieke `tx_key`.

## Belangrijkste functionaliteit

- **Multi-file import** met automatische typeherkenning (transacties vs positie/koersen).
- **Liquiditeiten/effecten-koppeling op referentie**; brokerbedrag komt uit liquiditeitenregel.
- **Transactieformules volgens notes** met vergelijking brokerbedrag vs formulebedrag en verschillenlijst.
- **0,1% transactiekostenregel** toegepast op aankoop/verkoop-berekeningen.
- **Opgelopen rente verwerkt** (EUR-basis) inclusief fallback-afleiding uit brokerbedrag.
- **Couponregels genormaliseerd**: `tx_currency = EUR`, `fx_rate = 1.0`.
- **Transactie-overzicht (excel stijl)** met edit/save, soft delete en verschilmonitoring.
- **Tijdelijke DB-resetknop** in UI voor testdoeleinden.
- **Instrumentverrijking bij transacties**:
  - valuta uit `Transactiebedrag valuta`,
  - couponpercentage uit naampatroon `(x,xx%)`,
  - einddatum uit naampatroon `dd-mm-jjjj`.
- **Analyse “Verkoop Nu”** houdt rekening met meeverkochte rente en additionele 0,1% verkoopkosten.

## Ontwikkelgebruik

```python
from bond_suite import Client, ProductCollection, TransactionManager, PortfolioBond, resultaten_tabel
```
