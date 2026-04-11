"""
SQL schema definitions (PostgreSQL style, SQLite compatible).

Tables
------
clients                        Client master data.
portfolios                     Portfolio definitions with base currency.
instruments                    Financial instrument catalogue (metadata as JSON).
cash_accounts                  Per-portfolio, per-currency cash accounts.
transactions                   Immutable transaction ledger (metadata as JSON).
instrument_attributes_history  Temporal attribute store for point-in-time queries.

Design choices
--------------
* JSON columns replace JSONB (SQLite limitation) — still allows flexible metadata.
* ``valid_from`` / ``valid_to`` on the attribute table supports reconstruction
  at any historical datetime **without snapshots**.
* Indexes on ``(instrument_id, timestamp)``, ``(portfolio_id, timestamp)``,
  and ``(instrument_id, valid_from, valid_to)`` optimise the most common
  analytic queries.
"""

SCHEMA_SQL = """
-- ===================================================================
-- Clients
-- ===================================================================
CREATE TABLE IF NOT EXISTS clients (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================================================
-- Portfolios
-- ===================================================================
CREATE TABLE IF NOT EXISTS portfolios (
    id              TEXT PRIMARY KEY,
    client_id       TEXT NOT NULL REFERENCES clients(id),
    name            TEXT,
    base_currency   TEXT NOT NULL DEFAULT 'EUR',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================================================
-- Instruments
-- ===================================================================
CREATE TABLE IF NOT EXISTS instruments (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN ('STOCK', 'BOND')),
    currency    TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}',          -- JSON blob
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================================================
-- Cash accounts (one per portfolio + currency)
-- ===================================================================
CREATE TABLE IF NOT EXISTS cash_accounts (
    id              TEXT PRIMARY KEY,
    portfolio_id    TEXT NOT NULL REFERENCES portfolios(id),
    currency        TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, currency)
);

-- ===================================================================
-- Transactions (immutable ledger)
-- ===================================================================
CREATE TABLE IF NOT EXISTS transactions (
    id              TEXT PRIMARY KEY,
    portfolio_id    TEXT NOT NULL REFERENCES portfolios(id),
    instrument_id   TEXT REFERENCES instruments(id),
    type            TEXT NOT NULL CHECK (type IN ('BUY', 'SELL', 'FEE', 'FX', 'INTEREST')),
    quantity        REAL NOT NULL DEFAULT 0,
    price           REAL NOT NULL DEFAULT 0,
    amount          REAL NOT NULL,
    currency        TEXT NOT NULL,
    timestamp       TIMESTAMP NOT NULL,
    metadata        TEXT DEFAULT '{}',      -- JSON blob
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================================================
-- Instrument attribute history (temporal dimension)
-- ===================================================================
CREATE TABLE IF NOT EXISTS instrument_attributes_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id       TEXT NOT NULL REFERENCES instruments(id),
    attribute_name      TEXT NOT NULL,
    attribute_value     TEXT NOT NULL,
    valid_from          TIMESTAMP NOT NULL,
    valid_to            TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================================================================
-- Indexes for analytic query performance
-- ===================================================================
CREATE INDEX IF NOT EXISTS idx_tx_instrument_ts
    ON transactions(instrument_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_tx_portfolio_ts
    ON transactions(portfolio_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_attr_validity
    ON instrument_attributes_history(instrument_id, valid_from, valid_to);
"""
