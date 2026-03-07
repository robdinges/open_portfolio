from __future__ import annotations

import sys
import sqlite3
import logging
import json
import re
from datetime import date, timedelta
from pathlib import Path
from io import StringIO
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st  # pyright: ignore[reportMissingImports]
import altair as alt

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from bond_suite import (  # noqa: E402
    Bond,
    CashMovement,
    Client,
    MarketDataStore,
    MovementType,
    PaymentFrequency,
    PortfolioBond,
    ProductCollection,
    Transaction,
    TransactionManager,
    TransactionTemplate,
)


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_FILE = DATA_DIR / "portfolio.db"
SCHEMA_VERSION = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bond_app")


def _log_event(event: str, level: str = "info", **context: object) -> None:
    payload = {"event": event, **context}
    message = json.dumps(payload, default=str, ensure_ascii=False)
    getattr(logger, level, logger.info)(message)


def _handle_error(user_message: str, exc: Exception | None = None, **context: object) -> None:
    if exc is not None:
        _log_event("error", level="error", message=user_message, exception=str(exc), **context)
    else:
        _log_event("error", level="error", message=user_message, **context)
    st.error(user_message)


def _db_connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS instruments (
                isin TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                currency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                maturity_date TEXT NOT NULL,
                interest_rate REAL NOT NULL,
                minimum_purchase_value REAL NOT NULL,
                smallest_trading_unit INTEGER NOT NULL,
                last_price_date TEXT,
                last_price REAL
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_account TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_key TEXT NOT NULL UNIQUE,
                tx_date TEXT NOT NULL,
                settlement_date TEXT,
                tx_type TEXT NOT NULL,
                description TEXT,
                account_id INTEGER NOT NULL,
                instrument_id TEXT,
                amount REAL,
                tx_cashflow REAL,
                tx_currency TEXT,
                fx_rate REAL,
                broker_amount REAL,
                formula_amount REAL,
                amount_difference REAL,
                price REAL,
                cost REAL,
                coupon REAL,
                source_file TEXT,
                reference TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS bond_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isin TEXT NOT NULL,
                price_date TEXT NOT NULL,
                currency TEXT NOT NULL,
                price REAL NOT NULL,
                UNIQUE(isin, price_date, currency)
            );

            CREATE TABLE IF NOT EXISTS fx_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate_date TEXT NOT NULL,
                rate REAL NOT NULL,
                UNIQUE(from_currency, to_currency, rate_date)
            );

            CREATE TABLE IF NOT EXISTS import_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_type TEXT NOT NULL,
                source_file TEXT,
                status TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                skipped_duplicates INTEGER DEFAULT 0,
                skipped_invalid INTEGER DEFAULT 0,
                message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        columns = {
            c["name"]
            for c in conn.execute("PRAGMA table_info(transactions)").fetchall()
        }
        if "is_deleted" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")
        if "tx_cashflow" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN tx_cashflow REAL")
        if "tx_currency" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN tx_currency TEXT")
        if "settlement_date" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN settlement_date TEXT")
        if "description" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN description TEXT")
        if "fx_rate" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN fx_rate REAL")
        if "broker_amount" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN broker_amount REAL")
        if "formula_amount" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN formula_amount REAL")
        if "amount_difference" not in columns:
            conn.execute("ALTER TABLE transactions ADD COLUMN amount_difference REAL")

        row = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        else:
            current_version = int(row["version"])
            if current_version < SCHEMA_VERSION:
                conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))

    _db_backfill_tx_cashflow()
    _db_backfill_tx_currency()
    _db_normalize_coupon_currency()
    _db_backfill_price_and_cost_defaults()
    _db_backfill_formula_amounts()
    _db_recompute_amount_differences()


def _db_get_or_create_account_id(external_account: str) -> int:
    normalized = external_account.strip()
    if not normalized:
        normalized = "UNKNOWN"
    with _db_connect() as conn:
        existing = conn.execute(
            "SELECT id FROM accounts WHERE external_account = ?",
            (normalized,),
        ).fetchone()
        if existing:
            return int(existing["id"])
        cursor = conn.execute(
            "INSERT INTO accounts(external_account) VALUES (?)",
            (normalized,),
        )
        return int(cursor.lastrowid)


def _db_backfill_tx_cashflow() -> None:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, tx_type, amount, price, cost, coupon
            FROM transactions
            WHERE tx_cashflow IS NULL
            """
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            tx_type = str(row["tx_type"] or "").strip().lower()
            tx_cashflow = _derive_tx_cashflow(
                tx_type=tx_type,
                amount=_coerce_optional_float(row["amount"], "amount"),
                price=_coerce_optional_float(row["price"], "price"),
                cost=_coerce_optional_float(row["cost"], "cost"),
                coupon=_coerce_optional_float(row["coupon"], "coupon"),
            )
            conn.execute(
                "UPDATE transactions SET tx_cashflow = ? WHERE id = ?",
                (tx_cashflow, int(row["id"])),
            )
            updated += 1

    _log_event("tx_cashflow_backfill", updated=updated)


def _db_backfill_tx_currency() -> None:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.instrument_id, t.tx_currency, i.currency AS instrument_currency
            FROM transactions t
            LEFT JOIN instruments i ON i.isin = t.instrument_id
            WHERE t.tx_currency IS NULL OR TRIM(t.tx_currency) = ''
            """
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            fill_currency = _normalize_currency(row["instrument_currency"], "EUR")
            conn.execute(
                "UPDATE transactions SET tx_currency = ? WHERE id = ?",
                (fill_currency, int(row["id"])),
            )
            updated += 1

    _log_event("tx_currency_backfill", updated=updated)


def _db_normalize_coupon_currency() -> None:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM transactions
            WHERE tx_type = 'coupon'
              AND (
                  tx_currency IS NULL
                  OR UPPER(TRIM(tx_currency)) <> 'EUR'
                  OR fx_rate IS NULL
                  OR ABS(fx_rate - 1.0) > 1e-9
              )
            """
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            conn.execute(
                "UPDATE transactions SET tx_currency = 'EUR', fx_rate = 1.0 WHERE id = ?",
                (int(row["id"]),),
            )
            updated += 1

    _log_event("coupon_currency_normalized", updated=updated)


def _db_backfill_price_and_cost_defaults() -> None:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, tx_type, price, cost
            FROM transactions
            WHERE price IS NULL OR cost IS NULL
            """
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            tx_type = str(row["tx_type"] or "").strip().lower()
            price = _coerce_optional_float(row["price"], "price")
            cost = _coerce_optional_float(row["cost"], "cost")

            if tx_type in {"coupon", "deposit", "withdrawal"}:
                if price is None:
                    price = 0.0
                if cost is None:
                    cost = 0.0
            elif tx_type == "aflossing" and cost is None:
                cost = 0.0

            conn.execute(
                "UPDATE transactions SET price = ?, cost = ? WHERE id = ?",
                (price, cost, int(row["id"])),
            )
            updated += 1

    _log_event("price_cost_defaults_backfill", updated=updated)


def _db_backfill_formula_amounts() -> None:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, tx_type, amount, price, coupon, cost, fx_rate, broker_amount
            FROM transactions
            WHERE formula_amount IS NULL
            """
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            tx_type = str(row["tx_type"] or "").strip().lower()
            canonical_type = {
                "buy": "aankoop",
                "sell": "verkoop",
                "coupon": "coupon betaling",
                "aflossing": "aflossing",
            }.get(tx_type)
            if not canonical_type:
                continue

            formula_amount = _calculate_formula_amount(
                tx_type=canonical_type,
                nominal=float(row["amount"] or 0.0),
                koers_decimal=float(row["price"] or 0.0),
                coupon_rente_eur=float(row["coupon"] or 0.0),
                valutakoers=float(row["fx_rate"] or 1.0),
                signed_cost=float(row["cost"] or 0.0),
            )
            broker_amount = _coerce_optional_float(row["broker_amount"], "broker_amount")
            formula_amount = _align_formula_amount_sign(formula_amount, canonical_type, broker_amount)
            amount_difference = None
            if formula_amount is not None and broker_amount is not None:
                amount_difference = broker_amount - formula_amount

            conn.execute(
                "UPDATE transactions SET formula_amount = ?, amount_difference = ? WHERE id = ?",
                (formula_amount, amount_difference, int(row["id"])),
            )
            updated += 1

    _log_event("formula_amount_backfill", updated=updated)


def _db_recompute_amount_differences() -> None:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, tx_type, amount, price, coupon, fx_rate, broker_amount
            FROM transactions
            WHERE broker_amount IS NOT NULL
            """
        ).fetchall()

        if not rows:
            return

        updated = 0
        for row in rows:
            tx_type = str(row["tx_type"] or "").strip().lower()
            canonical_type = {
                "buy": "aankoop",
                "sell": "verkoop",
                "coupon": "coupon betaling",
                "aflossing": "aflossing",
            }.get(tx_type, tx_type)
            broker_amount = _coerce_optional_float(row["broker_amount"], "broker_amount")
            nominal = float(row["amount"] or 0.0)
            koers_decimal = float(row["price"] or 0.0)
            valutakoers = float(row["fx_rate"] or 1.0)
            coupon_rente = float(row["coupon"] or 0.0)
            coupon_rente = _normalize_coupon_interest_for_trade(canonical_type, coupon_rente)
            if tx_type in {"buy", "sell"} and coupon_rente == 0.0:
                coupon_rente = _derive_coupon_interest_from_broker(
                    tx_type=canonical_type,
                    nominal=nominal,
                    koers_decimal=koers_decimal,
                    valutakoers=valutakoers,
                    broker_amount=float(broker_amount or 0.0),
                )
                coupon_rente = _normalize_coupon_interest_for_trade(canonical_type, coupon_rente)
            cost_magnitude = _calculate_cost_magnitude_eur(
                nominal=nominal,
                koers_decimal=koers_decimal,
                coupon_rente_eur=coupon_rente,
                valutakoers=valutakoers,
            )

            formula_amount = _calculate_formula_amount(
                tx_type=canonical_type,
                nominal=nominal,
                koers_decimal=koers_decimal,
                coupon_rente_eur=coupon_rente,
                valutakoers=valutakoers,
                signed_cost=_formula_signed_cost(canonical_type, cost_magnitude),
            )
            aligned_formula = _align_formula_amount_sign(formula_amount, canonical_type, broker_amount)
            amount_difference = None
            if aligned_formula is not None and broker_amount is not None:
                amount_difference = broker_amount - aligned_formula

            if tx_type in {"buy", "sell"}:
                conn.execute(
                    "UPDATE transactions SET coupon = ?, cost = ?, formula_amount = ?, amount_difference = ? WHERE id = ?",
                    (coupon_rente, cost_magnitude, aligned_formula, amount_difference, int(row["id"])),
                )
            else:
                conn.execute(
                    "UPDATE transactions SET formula_amount = ?, amount_difference = ? WHERE id = ?",
                    (aligned_formula, amount_difference, int(row["id"])),
                )
            updated += 1

    _log_event("amount_difference_recomputed", updated=updated)


def _db_upsert_instrument(
    isin: str,
    name: str,
    currency: str,
    start_date: date,
    maturity_date: date,
    interest_rate: float,
    minimum_purchase_value: float,
    smallest_trading_unit: int,
    last_price_date: date | None,
    last_price: float | None,
) -> None:
    with _db_connect() as conn:
        conn.execute(
            """
            INSERT INTO instruments (
                isin, name, currency, start_date, maturity_date, interest_rate,
                minimum_purchase_value, smallest_trading_unit, last_price_date, last_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(isin) DO UPDATE SET
                name = excluded.name,
                currency = excluded.currency,
                start_date = excluded.start_date,
                maturity_date = excluded.maturity_date,
                interest_rate = excluded.interest_rate,
                minimum_purchase_value = excluded.minimum_purchase_value,
                smallest_trading_unit = excluded.smallest_trading_unit,
                last_price_date = excluded.last_price_date,
                last_price = excluded.last_price
            """,
            (
                isin,
                name,
                currency,
                start_date.isoformat(),
                maturity_date.isoformat(),
                interest_rate,
                minimum_purchase_value,
                smallest_trading_unit,
                last_price_date.isoformat() if last_price_date else None,
                last_price,
            ),
        )


def _db_load_instruments() -> list[sqlite3.Row]:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT isin, name, currency, start_date, maturity_date,
                   interest_rate, minimum_purchase_value, smallest_trading_unit,
                   last_price_date, last_price
            FROM instruments
            ORDER BY isin
            """
        ).fetchall()
    return list(rows)


def _db_update_instrument_row(record: dict[str, object]) -> None:
    isin = str(record.get("isin") or "").strip()
    if not isin:
        raise ValueError("ISIN mag niet leeg zijn")

    name = str(record.get("name") or "").strip()
    currency = _normalize_currency(record.get("currency"), "EUR")

    start_date = pd.to_datetime(record.get("start_date"), errors="coerce")
    maturity_date = pd.to_datetime(record.get("maturity_date"), errors="coerce")
    if pd.isna(start_date) or pd.isna(maturity_date):
        raise ValueError(f"Ongeldige start/einddatum voor {isin}")

    interest_rate = _coerce_optional_float(record.get("interest_rate"), "interest_rate")
    minimum_purchase_value = _coerce_optional_float(
        record.get("minimum_purchase_value"), "minimum_purchase_value"
    )
    smallest_trading_unit = int(record.get("smallest_trading_unit") or 1)

    if interest_rate is None:
        interest_rate = 0.0
    if minimum_purchase_value is None:
        minimum_purchase_value = 1000.0

    with _db_connect() as conn:
        conn.execute(
            """
            UPDATE instruments
            SET name = ?,
                currency = ?,
                start_date = ?,
                maturity_date = ?,
                interest_rate = ?,
                minimum_purchase_value = ?,
                smallest_trading_unit = ?
            WHERE isin = ?
            """,
            (
                name or isin,
                currency,
                start_date.date().isoformat(),
                maturity_date.date().isoformat(),
                float(interest_rate),
                float(minimum_purchase_value),
                smallest_trading_unit,
                isin,
            ),
        )


def _db_load_transaction_keys() -> set[str]:
    with _db_connect() as conn:
        rows = conn.execute("SELECT tx_key FROM transactions WHERE is_deleted = 0").fetchall()
    return {str(row["tx_key"]) for row in rows}


def _db_log_import(
    import_type: str,
    source_file: str | None,
    status: str,
    processed: int = 0,
    skipped_duplicates: int = 0,
    skipped_invalid: int = 0,
    message: str | None = None,
) -> None:
    with _db_connect() as conn:
        conn.execute(
            """
            INSERT INTO import_log (
                import_type, source_file, status, processed,
                skipped_duplicates, skipped_invalid, message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_type,
                source_file,
                status,
                processed,
                skipped_duplicates,
                skipped_invalid,
                message,
            ),
        )


def _db_insert_transaction(
    tx_key: str,
    tx_date: date,
    settlement_date: date | None,
    tx_type: str,
    description: str | None,
    account_id: int,
    instrument_id: str | None,
    amount: float | None,
    tx_cashflow: float | None,
    tx_currency: str | None,
    fx_rate: float | None,
    broker_amount: float | None,
    formula_amount: float | None,
    amount_difference: float | None,
    price: float | None,
    cost: float | None,
    coupon: float | None,
    source_file: str | None,
    reference: str | None,
) -> bool:
    with _db_connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO transactions (
                    tx_key, tx_date, settlement_date, tx_type, description, account_id, instrument_id,
                    amount, tx_cashflow, tx_currency, fx_rate, broker_amount, formula_amount, amount_difference,
                    price, cost, coupon, source_file, reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_key,
                    tx_date.isoformat(),
                    settlement_date.isoformat() if settlement_date else None,
                    tx_type,
                    description,
                    account_id,
                    instrument_id,
                    amount,
                    tx_cashflow,
                    tx_currency,
                    fx_rate,
                    broker_amount,
                    formula_amount,
                    amount_difference,
                    price,
                    cost,
                    coupon,
                    source_file,
                    reference,
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def _db_soft_delete_transaction(tx_id: int) -> None:
    with _db_connect() as conn:
        conn.execute("UPDATE transactions SET is_deleted = 1 WHERE id = ?", (tx_id,))


def _db_load_transactions() -> list[sqlite3.Row]:
    with _db_connect() as conn:
        rows = conn.execute(
            """
            SELECT id, tx_key, tx_date, settlement_date, tx_type, description, account_id, instrument_id,
                     amount, tx_cashflow, tx_currency, fx_rate, broker_amount, formula_amount, amount_difference,
                     price, cost, coupon, source_file, reference
            FROM transactions
            WHERE is_deleted = 0
            ORDER BY tx_date, id
            """
        ).fetchall()
    return list(rows)


def _db_transactions_dataframe() -> pd.DataFrame:
    with _db_connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                t.id,
                t.tx_date,
                t.settlement_date,
                t.tx_type,
                t.description,
                t.account_id,
                a.external_account,
                t.instrument_id,
                i.name AS instrument_name,
                t.amount,
                t.tx_cashflow,
                t.tx_currency,
                t.fx_rate,
                t.broker_amount,
                t.formula_amount,
                t.amount_difference,
                t.price,
                t.cost,
                t.coupon,
                t.reference,
                t.tx_key,
                t.source_file
            FROM transactions t
            LEFT JOIN accounts a ON a.id = t.account_id
            LEFT JOIN instruments i ON i.isin = t.instrument_id
            WHERE t.is_deleted = 0
            ORDER BY t.tx_date, t.id
            """,
            conn,
        )
    return df


def _db_update_transaction_row(record: dict) -> None:
    tx_id = int(record["id"])
    tx_date = pd.to_datetime(record.get("tx_date"), errors="coerce")
    if pd.isna(tx_date):
        raise ValueError(f"Ongeldige tx_date voor id={tx_id}")
    settlement_date = pd.to_datetime(record.get("settlement_date"), errors="coerce")

    instrument_id = str(record.get("instrument_id") or "").strip() or None
    if instrument_id and not st.session_state.product_collection.search_product_id(instrument_id):
        raise ValueError(f"Onbekende ISIN in edit: {instrument_id}")

    tx_type = str(record.get("tx_type") or "").strip().lower()
    valid_types = {"buy", "sell", "aflossing", "coupon", "deposit", "withdrawal"}
    if tx_type not in valid_types:
        raise ValueError(f"Onbekend tx_type '{tx_type}' voor id={tx_id}")

    _validate_db_transaction_record(record)

    amount = _coerce_optional_float(record.get("amount"), "amount")
    price = _coerce_optional_float(record.get("price"), "price")
    cost = _coerce_optional_float(record.get("cost"), "cost")
    coupon = _coerce_optional_float(record.get("coupon"), "coupon")
    fx_rate = _coerce_optional_float(record.get("fx_rate"), "fx_rate")
    if fx_rate is not None and fx_rate <= 0:
        raise ValueError("fx_rate moet > 0 zijn")

    tx_type_for_formula = {
        "buy": "aankoop",
        "sell": "verkoop",
        "coupon": "coupon betaling",
        "aflossing": "aflossing",
    }.get(tx_type, tx_type)

    derived_cost_magnitude = _calculate_cost_magnitude_eur(
        nominal=float(amount or 0.0),
        koers_decimal=float(price or 0.0),
        coupon_rente_eur=float(coupon or 0.0),
        valutakoers=float(fx_rate or 1.0),
    )
    if tx_type in {"buy", "sell"}:
        cost = derived_cost_magnitude

    formula_amount = _calculate_formula_amount(
        tx_type=tx_type_for_formula,
        nominal=float(amount or 0.0),
        koers_decimal=float(price or 0.0),
        coupon_rente_eur=float(coupon or 0.0),
        valutakoers=float(fx_rate or 1.0),
        signed_cost=_formula_signed_cost(tx_type_for_formula, derived_cost_magnitude),
    )
    broker_amount = _coerce_optional_float(record.get("broker_amount"), "broker_amount")
    formula_amount = _align_formula_amount_sign(formula_amount, tx_type_for_formula, broker_amount)
    amount_difference = None
    if formula_amount is not None and broker_amount is not None:
        amount_difference = broker_amount - formula_amount

    tx_cashflow = _derive_tx_cashflow(tx_type, amount, price, cost, coupon)

    with _db_connect() as conn:
        conn.execute(
            """
            UPDATE transactions
            SET tx_date = ?,
                settlement_date = ?,
                tx_type = ?,
                description = ?,
                account_id = ?,
                instrument_id = ?,
                amount = ?,
                tx_cashflow = ?,
                tx_currency = ?,
                fx_rate = ?,
                formula_amount = ?,
                amount_difference = ?,
                price = ?,
                cost = ?,
                coupon = ?,
                reference = ?
            WHERE id = ?
            """,
            (
                tx_date.date().isoformat(),
                settlement_date.date().isoformat() if pd.notna(settlement_date) else None,
                tx_type,
                str(record.get("description") or "").strip() or None,
                int(record.get("account_id") or 0),
                instrument_id,
                amount,
                tx_cashflow,
                str(record.get("tx_currency") or "").strip() or None,
                fx_rate,
                formula_amount,
                amount_difference,
                price,
                cost,
                coupon,
                str(record.get("reference") or "").strip() or None,
                tx_id,
            ),
        )


def _reset_runtime_state_and_reload() -> None:
    keys_to_clear = [
        "client",
        "portfolio",
        "product_collection",
        "transaction_manager",
        "market_data",
        "obligaties",
        "instrument_options",
        "transaction_keys",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def _reset_database_for_testing() -> None:
    if DB_FILE.exists():
        DB_FILE.unlink()
    _init_db()
    _reset_runtime_state_and_reload()
    init_state()


def _db_upsert_bond_price(isin: str, price_date: date, currency: str, price: float) -> bool:
    with _db_connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO bond_prices (isin, price_date, currency, price)
                VALUES (?, ?, ?, ?)
                """,
                (isin, price_date.isoformat(), currency, price),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def _db_upsert_fx_rate(from_currency: str, to_currency: str, rate_date: date, rate: float) -> bool:
    with _db_connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO fx_rates (from_currency, to_currency, rate_date, rate)
                VALUES (?, ?, ?, ?)
                """,
                (from_currency, to_currency, rate_date.isoformat(), rate),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def _db_load_bond_prices() -> list[sqlite3.Row]:
    with _db_connect() as conn:
        rows = conn.execute("SELECT isin, price_date, currency, price FROM bond_prices ORDER BY price_date").fetchall()
    return list(rows)


def _db_bond_prices_dataframe() -> pd.DataFrame:
    with _db_connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                b.isin,
                i.name AS instrument_name,
                b.currency,
                b.price_date,
                b.price
            FROM bond_prices b
            LEFT JOIN instruments i ON i.isin = b.isin
            ORDER BY b.price_date DESC, b.isin
            """,
            conn,
        )
    return df


def _db_load_fx_rates() -> list[sqlite3.Row]:
    with _db_connect() as conn:
        rows = conn.execute(
            "SELECT from_currency, to_currency, rate_date, rate FROM fx_rates ORDER BY rate_date"
        ).fetchall()
    return list(rows)


def _to_float(value: object, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_float_eu(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return default


def _normalize_currency(value: object, fallback: str = "EUR") -> str:
    if value is None:
        return fallback
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return fallback
    return text


def _format_date_display(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return "-"
    return parsed.strftime("%d-%m-%Y")


def _format_date_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column in df.columns:
        parsed = pd.to_datetime(df[column], errors="coerce")
        df[column] = parsed.dt.strftime("%d-%m-%Y").fillna("")
    return df


def _coerce_optional_float(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Ongeldige waarde voor {field_name}: {value}") from exc


def _validate_db_transaction_record(record: dict[str, object]) -> None:
    tx_type = str(record.get("tx_type") or "").strip().lower()
    amount = _coerce_optional_float(record.get("amount"), "amount")
    price = _coerce_optional_float(record.get("price"), "price")
    cost = _coerce_optional_float(record.get("cost"), "cost")
    coupon = _coerce_optional_float(record.get("coupon"), "coupon")

    if tx_type in {"buy", "sell", "aflossing"}:
        if amount is None or amount <= 0:
            raise ValueError("amount moet > 0 zijn voor buy/sell/aflossing")
        if price is None or price <= 0:
            raise ValueError("price moet > 0 zijn voor buy/sell/aflossing")
        if tx_type == "aflossing" and (cost is not None and cost != 0.0):
            raise ValueError("cost moet 0 zijn voor aflossing")
    elif tx_type == "coupon":
        if coupon is None or coupon == 0:
            raise ValueError("coupon moet gevuld en != 0 zijn voor coupon transactie")
    elif tx_type in {"deposit", "withdrawal"}:
        if amount is None or amount == 0:
            raise ValueError("amount moet gevuld en != 0 zijn voor deposit/withdrawal")


def _derive_tx_cashflow(
    tx_type: str,
    amount: float | None,
    price: float | None,
    cost: float | None,
    coupon: float | None,
    broker_transactiebedrag: float | None = None,
) -> float:
    if broker_transactiebedrag is not None and broker_transactiebedrag != 0:
        return float(broker_transactiebedrag)

    base_amount = float(amount or 0.0)
    base_price = float(price or 0.0)
    base_cost = float(cost or 0.0)
    base_coupon = float(coupon or 0.0)

    if tx_type == "buy":
        return -((abs(base_amount) * abs(base_price)) + abs(base_cost))
    if tx_type == "sell":
        return (abs(base_amount) * abs(base_price)) - abs(base_cost)
    if tx_type == "aflossing":
        return abs(base_amount) * abs(base_price)
    if tx_type == "coupon":
        if base_amount != 0:
            return base_amount
        return base_coupon
    if tx_type in {"deposit", "withdrawal"}:
        return base_amount
    return base_amount


def _calculate_formula_amount(
    tx_type: str,
    nominal: float,
    koers_decimal: float,
    coupon_rente_eur: float,
    valutakoers: float,
    signed_cost: float,
) -> float | None:
    normalized = tx_type.strip().lower()
    if normalized == "aankoop":
        return ((nominal * koers_decimal * valutakoers) + coupon_rente_eur) + signed_cost
    if normalized == "verkoop":
        return ((nominal * koers_decimal * valutakoers) + coupon_rente_eur) + signed_cost
    if normalized == "coupon betaling":
        return coupon_rente_eur
    if normalized == "aflossing":
        redemption_koers = koers_decimal if koers_decimal > 0 else 1.0
        return nominal * redemption_koers * valutakoers
    return None


def _calculate_cost_magnitude_eur(
    nominal: float,
    koers_decimal: float,
    coupon_rente_eur: float,
    valutakoers: float,
) -> float:
    trade_value_eur = (nominal * koers_decimal * valutakoers) + coupon_rente_eur
    return abs(trade_value_eur) * 0.001


def _formula_signed_cost(canonical_type: str, cost_magnitude: float) -> float:
    normalized = canonical_type.strip().lower()
    if normalized in {"aankoop", "buy"}:
        return abs(cost_magnitude)
    if normalized in {"verkoop", "sell"}:
        return -abs(cost_magnitude)
    return 0.0


def _align_formula_amount_sign(
    formula_amount: float | None,
    canonical_type: str,
    broker_amount: float | None,
) -> float | None:
    if formula_amount is None:
        return None

    magnitude = abs(float(formula_amount))
    if broker_amount is not None and broker_amount != 0:
        return magnitude if broker_amount > 0 else -magnitude

    normalized = canonical_type.strip().lower()
    if normalized in {"aankoop", "buy"}:
        return -magnitude
    return magnitude


def _parse_date_ddmmyyyy(value: object) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    parsed = pd.to_datetime(text, format="%d-%m-%Y", errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _load_transaction_keys() -> set[str]:
    return _db_load_transaction_keys()


def _save_transaction_keys(keys: set[str]) -> None:
    st.session_state.transaction_keys = keys


def _normalize_reference_key(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.endswith(".0"):
        maybe_int = raw[:-2]
        if maybe_int.isdigit():
            return maybe_int
    return raw


def _is_liquidity_transaction_row(row: pd.Series) -> bool:
    noteringseenheid = str(row.get("Noteringseenheid") or "").strip().lower()
    transactietype = str(row.get("Transactietype") or "").strip().lower()
    beleggingscategorie = str(row.get("Beleggingscategorie") or "").strip().lower()

    if "liquid" in noteringseenheid or "liquid" in beleggingscategorie:
        return True
    if "geld" in transactietype:
        return True
    return False


def _extract_broker_amount_from_row(row: pd.Series) -> float:
    candidate_columns = [
        "Bedrag in EUR",
        "Bedrag rekeningvaluta",
        "Netto bedrag",
        "Mutatie",
        "Transactiebedrag",
        "Bedrag",
    ]

    tx_currency = str(row.get("Transactiebedrag valuta") or "").strip().upper()
    for column in candidate_columns:
        if column not in row.index:
            continue
        value = _to_float_eu(row.get(column), 0.0)
        if value != 0:
            if column == "Transactiebedrag" and tx_currency not in {"", "EUR"}:
                continue
            return value
    return _to_float_eu(row.get("Transactiebedrag"), 0.0)


def _liquidity_row_rank(row: pd.Series) -> tuple[int, int, float]:
    tx_type = str(row.get("Transactietype") or "").strip().lower()
    tx_currency = str(row.get("Transactiebedrag valuta") or "").strip().upper()
    has_eur = 1 if tx_currency == "EUR" else 0
    is_geld_boeking = 1 if "geld" in tx_type else 0
    amount_abs = abs(_extract_broker_amount_from_row(row))
    return (has_eur, is_geld_boeking, amount_abs)


def _extract_coupon_interest_from_rows(row: pd.Series, liquidity_row: pd.Series | None) -> float:
    candidate_columns = [
        "Couponrente",
        "Opgelopen rente",
        "Meegekochte rente",
        "Meeverkochte rente",
        "Rente",
        "Accrued interest",
    ]
    rows = [row]
    if liquidity_row is not None:
        rows.append(liquidity_row)

    for candidate_row in rows:
        for column in candidate_columns:
            if column not in candidate_row.index:
                continue
            value = _to_float_eu(candidate_row.get(column), 0.0)
            if value != 0:
                return value
    return 0.0


def _derive_coupon_interest_from_broker(
    tx_type: str,
    nominal: float,
    koers_decimal: float,
    valutakoers: float,
    broker_amount: float,
) -> float:
    if nominal <= 0 or koers_decimal <= 0 or valutakoers <= 0 or broker_amount == 0:
        return 0.0

    normalized = tx_type.strip().lower()
    broker_abs = abs(broker_amount)
    if normalized == "aankoop":
        base_eur = broker_abs / 1.001
    elif normalized == "verkoop":
        base_eur = broker_abs / 0.999
    else:
        return 0.0

    accrued_interest = base_eur - (nominal * koers_decimal * valutakoers)
    if abs(accrued_interest) < 1e-9:
        return 0.0
    return abs(accrued_interest)


def _normalize_coupon_interest_for_trade(tx_type: str, coupon_interest: float) -> float:
    normalized = tx_type.strip().lower()
    if normalized in {"aankoop", "verkoop", "buy", "sell"}:
        return abs(coupon_interest)
    return coupon_interest


def _build_transaction_key(row: pd.Series) -> str:
    reference = _normalize_reference_key(row.get("Referentie"))
    if reference:
        return reference

    account = str(row.get("Rekeningnummer") or "").strip()
    book_date = str(row.get("Boekdatum") or "").strip()
    isin = str(row.get("ISIN") or "").strip()
    tx_type = str(row.get("Transactietype") or "").strip()
    nominal = str(row.get("Aantal / nominaal") or "").strip()
    return "|".join([account, book_date, isin, tx_type, nominal])


def _extract_bond_metadata_from_name(name: str) -> tuple[date | None, float | None]:
    maturity_date: date | None = None
    interest_rate: float | None = None

    date_match = re.search(r"\b(\d{2}-\d{2}-\d{4})\b", name)
    if date_match:
        parsed = pd.to_datetime(date_match.group(1), format="%d-%m-%Y", errors="coerce")
        if pd.notna(parsed):
            maturity_date = parsed.date()

    rate_match = re.search(r"\(\s*([0-9]+(?:[.,][0-9]+)?)\s*%\s*\)", name)
    if rate_match:
        text_rate = rate_match.group(1).replace(",", ".")
        try:
            interest_rate = float(text_rate) / 100.0
        except ValueError:
            interest_rate = None

    return maturity_date, interest_rate


def _ensure_instrument_from_transaction_row(row: pd.Series) -> str | None:
    product_collection = st.session_state.product_collection

    isin = str(row.get("ISIN") or "").strip()
    if not isin:
        return None

    fonds = str(row.get("Fonds") or isin).strip()
    tx_currency = str(row.get("Transactiebedrag valuta") or row.get("Koers valuta") or "EUR").strip() or "EUR"
    book_date = _parse_date_ddmmyyyy(row.get("Boekdatum")) or date.today()
    koers = _to_float_eu(row.get("Koers"), 100.0)
    maturity_date_from_name, interest_rate_from_name = _extract_bond_metadata_from_name(fonds)

    existing = product_collection.search_product_id(isin)
    if existing:
        updated = False

        current_currency = str(getattr(existing, "issue_currency", "") or "").strip() or "EUR"
        if tx_currency and tx_currency != current_currency:
            existing.issue_currency = tx_currency
            updated = True

        current_interest_rate = float(getattr(existing, "interest_rate", 0.0) or 0.0)
        if interest_rate_from_name is not None and abs(current_interest_rate) < 1e-12:
            existing.interest_rate = interest_rate_from_name
            updated = True

        current_start = getattr(existing, "start_date", None)
        start_date = current_start if isinstance(current_start, date) else book_date
        current_maturity = getattr(existing, "maturity_date", None)
        fallback_like_maturity = not isinstance(current_maturity, date) or current_maturity <= (start_date + timedelta(days=370))
        if maturity_date_from_name is not None and fallback_like_maturity:
            existing.maturity_date = maturity_date_from_name
            updated = True

        if updated:
            _db_upsert_instrument(
                isin=isin,
                name=str(getattr(existing, "description", fonds) or fonds),
                currency=str(getattr(existing, "issue_currency", tx_currency) or tx_currency),
                start_date=start_date,
                maturity_date=getattr(existing, "maturity_date", maturity_date_from_name or (book_date + timedelta(days=365))),
                interest_rate=float(getattr(existing, "interest_rate", 0.0) or 0.0),
                minimum_purchase_value=float(getattr(existing, "minimum_purchase_value", 1000.0) or 1000.0),
                smallest_trading_unit=int(getattr(existing, "smallest_trading_unit", 1) or 1),
                last_price_date=book_date,
                last_price=koers / 100.0,
            )

        return isin

    currency = tx_currency
    maturity_date = maturity_date_from_name or (book_date + timedelta(days=365))
    interest_rate = interest_rate_from_name if interest_rate_from_name is not None else 0.0

    product = Bond(
        instrument_id=isin,
        description=fonds,
        minimum_purchase_value=1000.0,
        smallest_trading_unit=1,
        issue_currency=currency,
        start_date=book_date,
        maturity_date=maturity_date,
        interest_rate=interest_rate,
        interest_payment_frequency=PaymentFrequency.YEAR,
    )

    product.add_price(book_date, koers / 100.0)
    product_collection.add_product(product)

    _db_upsert_instrument(
        isin=isin,
        name=fonds,
        currency=currency,
        start_date=book_date,
        maturity_date=maturity_date,
        interest_rate=interest_rate,
        minimum_purchase_value=1000.0,
        smallest_trading_unit=1,
        last_price_date=book_date,
        last_price=koers / 100.0,
    )

    st.session_state.instrument_options[f"{isin} - {fonds}"] = isin

    return isin


def _import_transactions_csv(uploaded_file) -> dict[str, object]:
    source_file = getattr(uploaded_file, "name", None)
    try:
        content = uploaded_file.getvalue().decode("utf-8", errors="replace")
        df = pd.read_csv(StringIO(content), sep=";", dtype=str)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        _db_log_import(
            import_type="transactions",
            source_file=source_file,
            status="failed",
            message=f"Bestand niet leesbaar: {exc}",
        )
        _handle_error("Transactiebestand kan niet worden ingelezen.", exc, source_file=source_file)
        return {"ok": False, "error": "Bestand niet leesbaar."}

    required_columns = {
        "Rekeningnummer",
        "Boekdatum",
        "Transactietype",
        "Transactiebedrag",
        "Transactiebedrag valuta",
        "ISIN",
        "Fonds",
        "Noteringseenheid",
        "Referentie",
        "Aantal / nominaal",
        "Koers",
        "Couponrente",
    }
    missing = sorted(required_columns - set(df.columns))
    if missing:
        _db_log_import(
            import_type="transactions",
            source_file=source_file,
            status="failed",
            message=f"Ontbrekende kolommen: {', '.join(missing)}",
        )
        return {
            "ok": False,
            "import_type": "transactions",
            "error": f"Ontbrekende kolommen: {', '.join(missing)}",
        }

    notering_series = df["Noteringseenheid"].fillna("").astype(str).str.strip()
    transactions_df = df[notering_series.eq("Nominaal")].copy()
    liquidity_df = df[df.apply(_is_liquidity_transaction_row, axis=1)].copy()

    liquidity_by_reference: dict[str, pd.Series] = {}
    liquidity_rank_by_reference: dict[str, tuple[int, int, float]] = {}
    if not liquidity_df.empty:
        for _, lrow in liquidity_df.iterrows():
            ref = _normalize_reference_key(lrow.get("Referentie"))
            if not ref:
                continue
            candidate_rank = _liquidity_row_rank(lrow)
            existing = liquidity_by_reference.get(ref)
            if existing is None:
                liquidity_by_reference[ref] = lrow
                liquidity_rank_by_reference[ref] = candidate_rank
                continue

            existing_rank = liquidity_rank_by_reference.get(ref, (0, 0, 0.0))
            if candidate_rank >= existing_rank:
                liquidity_by_reference[ref] = lrow
                liquidity_rank_by_reference[ref] = candidate_rank

    transaction_manager = st.session_state.transaction_manager
    portfolio = st.session_state.portfolio
    product_collection = st.session_state.product_collection
    known_keys: set[str] = st.session_state.transaction_keys

    processed = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    created_instruments = 0
    messages: list[str] = []

    for _, row in transactions_df.iterrows():
        tx_key = _build_transaction_key(row)
        try:
            if tx_key in known_keys:
                skipped_duplicates += 1
                messages.append(f"Duplicate overgeslagen: {tx_key}")
                continue

            book_date = _parse_date_ddmmyyyy(row.get("Boekdatum"))
            if not book_date:
                skipped_invalid += 1
                messages.append(f"Ongeldige datum, regel overgeslagen: {tx_key}")
                continue

            isin_before = str(row.get("ISIN") or "").strip()
            existed_before = bool(product_collection.search_product_id(isin_before)) if isin_before else True
            instrument_id = _ensure_instrument_from_transaction_row(row)
            if not instrument_id:
                skipped_invalid += 1
                messages.append(f"Geen ISIN, regel overgeslagen: {tx_key}")
                continue
            if not existed_before:
                created_instruments += 1

            tx_type = str(row.get("Transactietype") or "").strip().lower()
            tx_type_source = str(row.get("Transactietype") or "").strip()
            external_account = str(row.get("Rekeningnummer") or "").strip()
            account_id = _db_get_or_create_account_id(external_account)
            reference_value = _normalize_reference_key(row.get("Referentie"))
            liquidity_row = liquidity_by_reference.get(reference_value)

            tx_currency_source = row
            if liquidity_row is not None:
                tx_currency_source = liquidity_row
            tx_currency = str(
                tx_currency_source.get("Transactiebedrag valuta")
                or tx_currency_source.get("Koers valuta")
                or row.get("Koers valuta")
                or "EUR"
            ).strip() or "EUR"
            description = str(row.get("Omschrijving") or row.get("Fonds") or "").strip() or None
            settlement_date = _parse_date_ddmmyyyy(row.get("Valutadatum"))
            nominal = abs(_to_float_eu(row.get("Aantal / nominaal"), 0.0))
            koers = _to_float_eu(row.get("Koers"), 0.0) / 100.0
            valutakoers = _to_float_eu(row.get("Valutakoers"), 1.0)
            if valutakoers == 0:
                valutakoers = 1.0
            coupon = _extract_coupon_interest_from_rows(row, liquidity_row)
            coupon = _normalize_coupon_interest_for_trade(tx_type, coupon)
            cost_magnitude = _calculate_cost_magnitude_eur(
                nominal=nominal,
                koers_decimal=koers,
                coupon_rente_eur=coupon,
                valutakoers=valutakoers,
            )
            signed_cost = _formula_signed_cost(tx_type, cost_magnitude)

            persisted_type = ""
            persisted_amount: float | None = None
            persisted_cashflow: float | None = None
            persisted_price: float | None = None
            persisted_cost: float | None = None
            persisted_coupon: float | None = None
            broker_source = liquidity_row if liquidity_row is not None else row
            broker_tx_amount = _extract_broker_amount_from_row(broker_source)
            if tx_type in {"aankoop", "verkoop"} and coupon == 0 and liquidity_row is not None:
                coupon = _derive_coupon_interest_from_broker(
                    tx_type=tx_type,
                    nominal=nominal,
                    koers_decimal=koers,
                    valutakoers=valutakoers,
                    broker_amount=broker_tx_amount,
                )
                coupon = _normalize_coupon_interest_for_trade(tx_type, coupon)
            if tx_type == "coupon betaling" and broker_tx_amount == 0 and coupon != 0:
                broker_tx_amount = coupon
            if tx_type == "coupon betaling":
                tx_currency = "EUR"
                valutakoers = 1.0

            formula_tx_type = {
                "aankoop": "aankoop",
                "verkoop": "verkoop",
                "coupon betaling": "coupon betaling",
                "aflossing": "aflossing",
            }.get(tx_type, tx_type_source)
            formula_amount = _calculate_formula_amount(
                tx_type=formula_tx_type,
                nominal=nominal,
                koers_decimal=koers,
                coupon_rente_eur=coupon,
                valutakoers=valutakoers,
                signed_cost=signed_cost,
            )
            formula_amount = _align_formula_amount_sign(formula_amount, formula_tx_type, broker_tx_amount)
            amount_difference = None
            if formula_amount is not None:
                amount_difference = broker_tx_amount - formula_amount
            if tx_type in {"aankoop", "verkoop", "aflossing"} and liquidity_row is None:
                messages.append(f"Geen liquiditeitenregel gevonden voor referentie: {reference_value}")

            if tx_type == "aankoop":
                if nominal <= 0 or koers <= 0:
                    skipped_invalid += 1
                    messages.append(f"Aankoop met ongeldige nominal/koers overgeslagen: {tx_key}")
                    continue
                persisted_type = "buy"
                persisted_amount = nominal
                persisted_price = koers
                persisted_cost = cost_magnitude
                persisted_coupon = coupon
                persisted_cashflow = _derive_tx_cashflow(
                    "buy",
                    amount=nominal,
                    price=koers,
                    cost=cost_magnitude,
                    coupon=None,
                    broker_transactiebedrag=broker_tx_amount,
                )
                transaction = transaction_manager.create_transaction(
                    transaction_date=book_date,
                    portfolio_id=portfolio.portfolio_id,
                    template=TransactionTemplate.BUY,
                    account_id=account_id,
                    product_id=instrument_id,
                    amount=nominal,
                    price=koers,
                    cost=cost_magnitude,
                )
                result = transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            elif tx_type == "verkoop":
                if nominal <= 0 or koers <= 0:
                    skipped_invalid += 1
                    messages.append(f"Verkoop met ongeldige nominal/koers overgeslagen: {tx_key}")
                    continue
                persisted_type = "sell"
                persisted_amount = nominal
                persisted_price = koers
                persisted_cost = cost_magnitude
                persisted_coupon = coupon
                persisted_cashflow = _derive_tx_cashflow(
                    "sell",
                    amount=nominal,
                    price=koers,
                    cost=cost_magnitude,
                    coupon=None,
                    broker_transactiebedrag=broker_tx_amount,
                )
                transaction = transaction_manager.create_transaction(
                    transaction_date=book_date,
                    portfolio_id=portfolio.portfolio_id,
                    template=TransactionTemplate.SELL,
                    account_id=account_id,
                    product_id=instrument_id,
                    amount=nominal,
                    price=koers,
                    cost=cost_magnitude,
                )
                result = transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            elif tx_type == "aflossing":
                redemption_price = koers if koers > 0 else 1.0
                if nominal <= 0:
                    skipped_invalid += 1
                    messages.append(f"Aflossing met ongeldige nominal overgeslagen: {tx_key}")
                    continue
                persisted_type = "aflossing"
                persisted_amount = nominal
                persisted_price = redemption_price
                persisted_cost = 0.0
                persisted_cashflow = _derive_tx_cashflow(
                    "aflossing",
                    amount=nominal,
                    price=redemption_price,
                    cost=0.0,
                    coupon=None,
                    broker_transactiebedrag=broker_tx_amount,
                )
                transaction = transaction_manager.create_transaction(
                    transaction_date=book_date,
                    portfolio_id=portfolio.portfolio_id,
                    template=TransactionTemplate.SELL,
                    account_id=account_id,
                    product_id=instrument_id,
                    amount=nominal,
                    price=redemption_price,
                    cost=0.0,
                )
                result = transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            elif tx_type == "coupon betaling":
                if coupon == 0:
                    skipped_invalid += 1
                    messages.append(f"Coupon betaling zonder couponrente overgeslagen: {tx_key}")
                    continue
                persisted_type = "coupon"
                persisted_amount = coupon
                persisted_coupon = coupon
                persisted_price = 0.0
                persisted_cost = 0.0
                persisted_cashflow = _derive_tx_cashflow(
                    "coupon",
                    amount=coupon,
                    price=None,
                    cost=None,
                    coupon=coupon,
                    broker_transactiebedrag=broker_tx_amount,
                )
                transaction = Transaction(
                    transaction_date=book_date,
                    portfolio_id=portfolio.portfolio_id,
                    account_id=account_id,
                )
                movement = CashMovement(
                    transaction=transaction,
                    amount_account_currency=coupon,
                    amount_original_currency=coupon,
                    movement_type=MovementType.INTEREST,
                    transaction_number=transaction.transaction_number,
                )
                transaction.add_cash_movement(movement)
                result = transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            else:
                skipped_invalid += 1
                messages.append(f"Onbekend transactietype overgeslagen ({tx_type}): {tx_key}")
                continue

            if any("successfully executed" in msg for msg in result):
                inserted = _db_insert_transaction(
                    tx_key=tx_key,
                    tx_date=book_date,
                    settlement_date=settlement_date,
                    tx_type=persisted_type,
                    description=description,
                    account_id=account_id,
                    instrument_id=instrument_id,
                    amount=persisted_amount,
                    tx_cashflow=persisted_cashflow,
                    tx_currency=tx_currency,
                    fx_rate=valutakoers,
                    broker_amount=broker_tx_amount,
                    formula_amount=formula_amount,
                    amount_difference=amount_difference,
                    price=persisted_price,
                    cost=persisted_cost,
                    coupon=persisted_coupon,
                    source_file=source_file,
                    reference=str(row.get("Referentie") or "").strip() or None,
                )
                if inserted:
                    processed += 1
                    known_keys.add(tx_key)
                    if amount_difference is not None and abs(amount_difference) >= 0.01:
                        messages.append(
                            (
                                f"Verschil transactiebedrag ({tx_key}) | "
                                f"broker={broker_tx_amount:.2f} | formule={formula_amount:.2f} | delta={amount_difference:.2f}"
                            )
                        )
                else:
                    skipped_duplicates += 1
                    messages.append(f"Duplicate (DB unique) overgeslagen: {tx_key}")
            else:
                skipped_invalid += 1
                messages.append(f"Niet verwerkt: {tx_key} -> {' | '.join(result)}")
        except (TypeError, ValueError, KeyError, RuntimeError, sqlite3.Error) as exc:
            skipped_invalid += 1
            _log_event("transaction_row_failed", level="warning", tx_key=tx_key, error=str(exc))
            messages.append(f"Fout bij verwerken van regel: {tx_key}")

    st.session_state.transaction_keys = known_keys
    _save_transaction_keys(known_keys)

    _db_log_import(
        import_type="transactions",
        source_file=source_file,
        status="success",
        processed=processed,
        skipped_duplicates=skipped_duplicates,
        skipped_invalid=skipped_invalid,
        message=f"created_instruments={created_instruments}",
    )

    _log_event(
        "transactions_imported",
        source_file=source_file,
        processed=processed,
        skipped_duplicates=skipped_duplicates,
        skipped_invalid=skipped_invalid,
        created_instruments=created_instruments,
    )

    return {
        "ok": True,
        "import_type": "transactions",
        "processed": processed,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
        "created_instruments": created_instruments,
        "messages": messages[:50],
    }


def _import_positions_csv(uploaded_file) -> dict[str, object]:
    source_file = getattr(uploaded_file, "name", None)
    try:
        content = uploaded_file.getvalue().decode("utf-8", errors="replace")
        df = pd.read_csv(StringIO(content), sep=";", dtype=str)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        _db_log_import(
            import_type="positions",
            source_file=source_file,
            status="failed",
            message=f"Bestand niet leesbaar: {exc}",
        )
        _handle_error("Positiebestand kan niet worden ingelezen.", exc, source_file=source_file)
        return {"ok": False, "error": "Bestand niet leesbaar."}

    required_columns = {
        "Beleggingscategorie",
        "Fondsnaam",
        "ISIN",
        "Koers",
        "Noteringsvaluta",
        "Koersdatum / - tijd",
    }
    missing = sorted(required_columns - set(df.columns))
    if missing:
        _db_log_import(
            import_type="positions",
            source_file=source_file,
            status="failed",
            message=f"Ontbrekende kolommen: {', '.join(missing)}",
        )
        return {
            "ok": False,
            "import_type": "positions",
            "error": f"Ontbrekende kolommen: {', '.join(missing)}",
        }

    bonds_df = df[df["Beleggingscategorie"].fillna("").str.strip().eq("Obligaties")].copy()
    if bonds_df.empty:
        return {
            "ok": True,
            "import_type": "positions",
            "processed": 0,
            "skipped_duplicates": 0,
            "skipped_invalid": 0,
            "created_instruments": 0,
            "messages": ["Geen Obligaties records gevonden."],
        }

    processed = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    created_instruments = 0
    messages: list[str] = []

    for _, row in bonds_df.iterrows():
        try:
            isin = str(row.get("ISIN") or "").strip()
            if not isin:
                skipped_invalid += 1
                messages.append("Regel zonder ISIN overgeslagen")
                continue

            name = str(row.get("Fondsnaam") or isin).strip()
            currency = str(row.get("Noteringsvaluta") or "EUR").strip() or "EUR"
            koers = _to_float_eu(row.get("Koers"), 0.0)
            raw_date = str(row.get("Koersdatum / - tijd") or "").strip()
            koers_dt = pd.to_datetime(raw_date, errors="coerce", dayfirst=True)
            if pd.isna(koers_dt) or koers <= 0:
                skipped_invalid += 1
                messages.append(f"Ongeldige koers of datum overgeslagen: {isin}")
                continue
            koers_date = koers_dt.date()

            product_collection = st.session_state.product_collection
            existing = product_collection.search_product_id(isin)
            if not existing:
                start_date = koers_date
                maturity_date = koers_date + timedelta(days=365)
                product = Bond(
                    instrument_id=isin,
                    description=name,
                    minimum_purchase_value=1000.0,
                    smallest_trading_unit=1,
                    issue_currency=currency,
                    start_date=start_date,
                    maturity_date=maturity_date,
                    interest_rate=0.0,
                    interest_payment_frequency=PaymentFrequency.YEAR,
                )
                product_collection.add_product(product)
                _db_upsert_instrument(
                    isin=isin,
                    name=name,
                    currency=currency,
                    start_date=start_date,
                    maturity_date=maturity_date,
                    interest_rate=0.0,
                    minimum_purchase_value=1000.0,
                    smallest_trading_unit=1,
                    last_price_date=koers_date,
                    last_price=koers / 100.0,
                )
                st.session_state.instrument_options[f"{isin} - {name}"] = isin
                created_instruments += 1

            inserted = _db_upsert_bond_price(isin, koers_date, currency, koers)
            if inserted:
                processed += 1
            else:
                skipped_duplicates += 1
        except (TypeError, ValueError, KeyError, sqlite3.Error) as exc:
            skipped_invalid += 1
            messages.append(f"Fout in regel: {exc}")

    _db_log_import(
        import_type="positions",
        source_file=source_file,
        status="success",
        processed=processed,
        skipped_duplicates=skipped_duplicates,
        skipped_invalid=skipped_invalid,
        message=f"created_instruments={created_instruments}",
    )

    return {
        "ok": True,
        "import_type": "positions",
        "processed": processed,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
        "created_instruments": created_instruments,
        "messages": messages[:50],
    }


def _import_uploaded_file(uploaded_file) -> dict[str, object]:
    try:
        content = uploaded_file.getvalue().decode("utf-8", errors="replace")
        df = pd.read_csv(StringIO(content), sep=";", dtype=str, nrows=5)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError):
        return {"ok": False, "error": "Bestand niet leesbaar."}

    position_signature = {
        "Beleggingscategorie",
        "Fondsnaam",
        "ISIN",
        "Koers",
        "Noteringsvaluta",
        "Koersdatum / - tijd",
    }
    transaction_signature = {
        "Boekdatum",
        "Transactietype",
        "ISIN",
        "Noteringseenheid",
        "Referentie",
    }

    columns = set(df.columns)
    if position_signature.issubset(columns):
        return _import_positions_csv(uploaded_file)
    if transaction_signature.issubset(columns):
        return _import_transactions_csv(uploaded_file)
    return {
        "ok": False,
        "error": "Onbekend bestandstype. Ondersteund: transacties of positie-overzicht.",
    }


def _build_products_from_csv(obligaties: list[dict]) -> ProductCollection:
    collection = ProductCollection()
    today = date.today()

    for record in obligaties:
        isin = str(record.get("isin") or "").strip()
        if not isin:
            continue

        description = str(record.get("naam") or isin)
        currency = str(record.get("valuta") or "EUR")
        minimum_purchase_value = _to_float(record.get("nominale_waarde"), 1000.0)
        smallest_trading_unit = 1
        start_date = record.get("settlement_datum") or today
        maturity_date = record.get("einddatum") or (today + timedelta(days=365))
        interest_rate = _to_float(record.get("couponrente_pct"), 0.0) / 100.0

        product = Bond(
            instrument_id=isin,
            description=description,
            minimum_purchase_value=minimum_purchase_value,
            smallest_trading_unit=smallest_trading_unit,
            issue_currency=currency,
            start_date=start_date,
            maturity_date=maturity_date,
            interest_rate=interest_rate,
            interest_payment_frequency=PaymentFrequency.YEAR,
        )

        csv_price_pct = _to_float(record.get("aankoop_koers_pct"), 100.0)
        product.add_price(today, csv_price_pct / 100.0)
        collection.add_product(product)

    return collection


def _sync_csv_instruments_to_db(obligaties: list[dict]) -> None:
    today = date.today()
    for record in obligaties:
        isin = str(record.get("isin") or "").strip()
        if not isin:
            continue
        start_date = record.get("settlement_datum") or today
        maturity_date = record.get("einddatum") or (today + timedelta(days=365))
        csv_price_pct = _to_float(record.get("aankoop_koers_pct"), 100.0)
        _db_upsert_instrument(
            isin=isin,
            name=str(record.get("naam") or isin),
            currency=str(record.get("valuta") or "EUR"),
            start_date=start_date,
            maturity_date=maturity_date,
            interest_rate=_to_float(record.get("couponrente_pct"), 0.0) / 100.0,
            minimum_purchase_value=_to_float(record.get("nominale_waarde"), 1000.0),
            smallest_trading_unit=1,
            last_price_date=today,
            last_price=csv_price_pct / 100.0,
        )


def _build_products_from_db() -> ProductCollection:
    collection = ProductCollection()
    rows = _db_load_instruments()
    today = date.today()
    for row in rows:
        start_date = pd.to_datetime(row["start_date"], errors="coerce")
        maturity_date = pd.to_datetime(row["maturity_date"], errors="coerce")
        start = start_date.date() if pd.notna(start_date) else today
        maturity = maturity_date.date() if pd.notna(maturity_date) else (today + timedelta(days=365))

        product = Bond(
            instrument_id=row["isin"],
            description=row["name"],
            minimum_purchase_value=float(row["minimum_purchase_value"]),
            smallest_trading_unit=int(row["smallest_trading_unit"]),
            issue_currency=row["currency"],
            start_date=start,
            maturity_date=maturity,
            interest_rate=float(row["interest_rate"]),
            interest_payment_frequency=PaymentFrequency.YEAR,
        )

        if row["last_price"] is not None:
            price_date = pd.to_datetime(row["last_price_date"], errors="coerce")
            p_date = price_date.date() if pd.notna(price_date) else today
            product.add_price(p_date, float(row["last_price"]))

        collection.add_product(product)
    return collection


def _replay_transactions_from_db() -> None:
    transaction_manager = st.session_state.transaction_manager
    portfolio = st.session_state.portfolio
    product_collection = st.session_state.product_collection

    rows = _db_load_transactions()
    for row in rows:
        try:
            tx_date = pd.to_datetime(row["tx_date"], errors="coerce")
            if pd.isna(tx_date):
                _log_event("replay_skip", level="warning", reason="invalid_date", tx_id=row["id"])
                continue
            tx_day = tx_date.date()
            tx_type = str(row["tx_type"] or "").lower()
            account_id = int(row["account_id"])

            if tx_type in {"buy", "sell", "aflossing"}:
                instrument_id = str(row["instrument_id"] or "").strip()
                if not instrument_id or not product_collection.search_product_id(instrument_id):
                    _log_event(
                        "replay_skip",
                        level="warning",
                        reason="unknown_instrument",
                        tx_id=row["id"],
                        instrument_id=instrument_id,
                    )
                    continue

                amount = float(row["amount"] or 0.0)
                price = float(row["price"] or 0.0)
                cost = float(row["cost"] or 0.0)
                if amount <= 0 or price <= 0:
                    _log_event(
                        "replay_skip",
                        level="warning",
                        reason="invalid_trade_values",
                        tx_id=row["id"],
                        amount=amount,
                        price=price,
                    )
                    continue

                template = TransactionTemplate.BUY if tx_type == "buy" else TransactionTemplate.SELL
                if tx_type == "aflossing":
                    cost = 0.0
                transaction = transaction_manager.create_transaction(
                    transaction_date=tx_day,
                    portfolio_id=portfolio.portfolio_id,
                    template=template,
                    account_id=account_id,
                    product_id=instrument_id,
                    amount=amount,
                    price=price,
                    cost=cost,
                )
                transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            elif tx_type == "coupon":
                coupon = float(row["coupon"] or 0.0)
                if coupon == 0:
                    _log_event("replay_skip", level="warning", reason="invalid_coupon", tx_id=row["id"])
                    continue
                transaction = Transaction(
                    transaction_date=tx_day,
                    portfolio_id=portfolio.portfolio_id,
                    account_id=account_id,
                )
                movement = CashMovement(
                    transaction=transaction,
                    amount_account_currency=coupon,
                    amount_original_currency=coupon,
                    movement_type=MovementType.INTEREST,
                    transaction_number=transaction.transaction_number,
                )
                transaction.add_cash_movement(movement)
                transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            elif tx_type in {"deposit", "withdrawal"}:
                amount = float(row["amount"] or 0.0)
                if amount == 0:
                    _log_event("replay_skip", level="warning", reason="invalid_cash_amount", tx_id=row["id"])
                    continue
                movement_type = MovementType.DEPOSIT if tx_type == "deposit" else MovementType.WITHDRAWAL
                transaction = Transaction(
                    transaction_date=tx_day,
                    portfolio_id=portfolio.portfolio_id,
                    account_id=account_id,
                )
                movement = CashMovement(
                    transaction=transaction,
                    amount_account_currency=amount,
                    amount_original_currency=amount,
                    movement_type=movement_type,
                    transaction_number=transaction.transaction_number,
                )
                transaction.add_cash_movement(movement)
                transaction_manager.execute_transaction(transaction, portfolio, product_collection)
            else:
                _log_event("replay_skip", level="warning", reason="unknown_tx_type", tx_id=row["id"], tx_type=tx_type)
        except (TypeError, ValueError, KeyError) as exc:
            _log_event("replay_error", level="warning", tx_id=row["id"], error=str(exc))


def _load_market_data_from_db() -> MarketDataStore:
    market_data = MarketDataStore()

    for row in _db_load_bond_prices():
        d = pd.to_datetime(row["price_date"], errors="coerce")
        if pd.isna(d):
            continue
        market_data.voeg_obligatiekoers_toe(row["isin"], d.date(), float(row["price"]))

    for row in _db_load_fx_rates():
        d = pd.to_datetime(row["rate_date"], errors="coerce")
        if pd.isna(d):
            continue
        if row["to_currency"] == "EUR":
            market_data.voeg_valutakoers_toe(row["from_currency"], d.date(), float(row["rate"]))

    return market_data


def _instrument_options_from_csv(obligaties: list[dict]) -> dict[str, str]:
    options: dict[str, str] = {}
    for record in obligaties:
        isin = str(record.get("isin") or "").strip()
        if not isin:
            continue
        naam = str(record.get("naam") or "Onbekend")
        options[f"{isin} - {naam}"] = isin
    return options


def init_state() -> None:
    if "portfolio" in st.session_state:
        return

    _init_db()

    obligaties: list[dict] = []
    product_collection = _build_products_from_db()
    transaction_manager = TransactionManager()

    client = Client(client_id=1, name="Demo Client")
    portfolio = client.add_portfolio(portfolio_id=1)
    portfolio.add_cash_account(account_id=123, start_balance=10000)

    st.session_state.client = client
    st.session_state.portfolio = portfolio
    st.session_state.product_collection = product_collection
    st.session_state.transaction_manager = transaction_manager
    st.session_state.market_data = _load_market_data_from_db()
    st.session_state.obligaties = obligaties
    st.session_state.instrument_options = {}
    st.session_state.transaction_keys = _load_transaction_keys()

    for isin, product in st.session_state.product_collection.products.items():
        label = f"{isin} - {product.description}"
        st.session_state.instrument_options[label] = isin

    _replay_transactions_from_db()


def movement_type_for_cash(transaction_kind: str) -> MovementType:
    return MovementType.DEPOSIT if transaction_kind == "DEPOSIT" else MovementType.WITHDRAWAL


def show_bond_timeline() -> None:
    st.subheader("Obligatie-tijdlijn")

    tx_df = _db_transactions_dataframe()
    if tx_df.empty:
        st.info("Nog geen transacties in database.")
        return

    tx_bonds_df = tx_df[
        tx_df["instrument_id"].notna() & tx_df["tx_type"].isin(["buy", "sell", "aflossing", "coupon"])
    ].copy()
    tx_bonds_df["instrument_id"] = tx_bonds_df["instrument_id"].astype(str).str.strip()
    tx_bonds_df = tx_bonds_df[tx_bonds_df["instrument_id"] != ""]

    if tx_bonds_df.empty:
        st.info("Nog geen obligatietransacties beschikbaar.")
        return

    label_map: dict[str, str] = {}
    for isin, group in tx_bonds_df.groupby("instrument_id"):
        name_candidates = group["instrument_name"].dropna().astype(str).str.strip()
        bond_name = name_candidates.iloc[0] if not name_candidates.empty else isin
        label_map[isin] = f"{isin} - {bond_name}"

    bond_options = {
        label_map[isin]: isin
        for isin in sorted(label_map.keys())
    }
    if not bond_options:
        st.info("Geen obligaties met transacties beschikbaar.")
        return

    if "timeline_selected_isins" not in st.session_state:
        st.session_state.timeline_selected_isins = list(bond_options.values())

    selected_from_checkboxes: list[str] = []
    selected_state = set(st.session_state.timeline_selected_isins)

    with st.expander("Selecteer obligaties", expanded=False):
        select_col1, select_col2 = st.columns(2)
        if select_col1.button("Select all", key="timeline_select_all"):
            st.session_state.timeline_selected_isins = list(bond_options.values())
            for isin in bond_options.values():
                st.session_state[f"timeline_isin_{isin}"] = True
            st.rerun()
        if select_col2.button("Select none", key="timeline_select_none"):
            st.session_state.timeline_selected_isins = []
            for isin in bond_options.values():
                st.session_state[f"timeline_isin_{isin}"] = False
            st.rerun()

        for label, isin in bond_options.items():
            if st.checkbox(label, value=isin in selected_state, key=f"timeline_isin_{isin}"):
                selected_from_checkboxes.append(isin)

    st.session_state.timeline_selected_isins = selected_from_checkboxes
    if not selected_from_checkboxes:
        st.info("Selecteer minimaal één obligatie om de tijdlijn te tonen.")
        return

    selected_isins = set(selected_from_checkboxes)
    event_types = {
        "buy": "Aankoop",
        "coupon": "Rente ontvangen",
        "sell": "Verkoop",
        "aflossing": "Redemption",
    }

    st.markdown("**Toon bedragen in grafiek**")
    t1, t2, t3, t4 = st.columns(4)
    show_buy = t1.checkbox("Aankoop", value=True, key="timeline_show_buy")
    show_sell = t2.checkbox("Verkoop", value=True, key="timeline_show_sell")
    show_redemption = t3.checkbox("Redemption", value=True, key="timeline_show_redemption")
    show_coupon = t4.checkbox("Couponrente", value=True, key="timeline_show_coupon")

    visible_tx_types: list[str] = []
    if show_buy:
        visible_tx_types.append("buy")
    if show_sell:
        visible_tx_types.append("sell")
    if show_redemption:
        visible_tx_types.append("aflossing")
    if show_coupon:
        visible_tx_types.append("coupon")

    if not visible_tx_types:
        st.info("Selecteer minimaal één bedragtype voor de grafiek.")
        return

    events = tx_df[
        tx_df["tx_type"].isin(event_types.keys())
        & tx_df["instrument_id"].isin(selected_isins)
    ].copy()

    if events.empty:
        st.info("Geen events gevonden voor de geselecteerde obligaties.")
        return

    events["tx_date"] = pd.to_datetime(events["tx_date"], errors="coerce")
    events = events.dropna(subset=["tx_date"])
    if events.empty:
        st.info("Geen geldige datums gevonden in events.")
        return

    min_date = events["tx_date"].dt.date.min()
    max_date = events["tx_date"].dt.date.max()
    date_start, date_end = st.slider(
        "Periode",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="DD-MM-YYYY",
        key="timeline_period_slider",
    )
    events = events[
        (events["tx_date"].dt.date >= date_start)
        & (events["tx_date"].dt.date <= date_end)
    ].copy()
    if events.empty:
        st.info("Geen events in de geselecteerde periode.")
        return

    events["event"] = events["tx_type"].map(event_types)
    events["instrument_label"] = events.apply(
        lambda row: f"{row['instrument_id']} - {row['instrument_name'] or row['instrument_id']}",
        axis=1,
    )
    events["transactiebedrag"] = pd.to_numeric(events["tx_cashflow"], errors="coerce")
    legacy_missing = events["transactiebedrag"].isna()
    if legacy_missing.any():
        legacy = events[legacy_missing].copy()
        legacy["legacy_cashflow"] = legacy.apply(
            lambda row: _derive_tx_cashflow(
                str(row["tx_type"] or ""),
                _coerce_optional_float(row.get("amount"), "amount"),
                _coerce_optional_float(row.get("price"), "price"),
                _coerce_optional_float(row.get("cost"), "cost"),
                _coerce_optional_float(row.get("coupon"), "coupon"),
            ),
            axis=1,
        )
        events.loc[legacy_missing, "transactiebedrag"] = legacy["legacy_cashflow"].values
    events["transactiebedrag"] = events["transactiebedrag"].fillna(0.0)
    events["rente_ontvangen"] = events.apply(
        lambda row: float(row["transactiebedrag"]) if row["tx_type"] == "coupon" else 0.0,
        axis=1,
    )
    events["aankoop_nominaal"] = events.apply(
        lambda row: float(row["transactiebedrag"]) if row["tx_type"] == "buy" else 0.0,
        axis=1,
    )
    events["verkoop_nominaal"] = events.apply(
        lambda row: float(row["transactiebedrag"]) if row["tx_type"] == "sell" else 0.0,
        axis=1,
    )
    events["aflossing_nominaal"] = events.apply(
        lambda row: float(row["transactiebedrag"]) if row["tx_type"] == "aflossing" else 0.0,
        axis=1,
    )
    events = events[events["tx_type"].isin(visible_tx_types)].copy()
    if events.empty:
        st.info("Geen events voor de geselecteerde bedragtypes.")
        return

    events = events.sort_values(["tx_date", "instrument_label", "id"])

    events["cum_aankoop"] = events["aankoop_nominaal"].cumsum()
    events["cum_verkoop"] = events["verkoop_nominaal"].cumsum()
    events["cum_aflossing"] = events["aflossing_nominaal"].cumsum()
    events["cum_transactiebedrag"] = events["transactiebedrag"].cumsum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rente ontvangen", f"€ {events['rente_ontvangen'].sum():,.2f}")
    m2.metric("Cumul aankoop", f"{events['cum_aankoop'].iloc[-1]:,.2f}")
    m3.metric("Cumul verkoop", f"{events['cum_verkoop'].iloc[-1]:,.2f}")
    m4.metric("Cumul aflossing", f"{events['cum_aflossing'].iloc[-1]:,.2f}")

    points = (
        alt.Chart(events)
        .mark_point(size=140, filled=True)
        .encode(
            x=alt.X(
                "tx_date:T",
                title="Datum (maand/jaar)",
                axis=alt.Axis(format="%m/%Y", labelAngle=-45),
            ),
            y=alt.Y("transactiebedrag:Q", title="Transactiebedrag"),
            shape=alt.Shape("event:N", title="Event"),
            tooltip=[
                alt.Tooltip("tx_date:T", title="Datum"),
                alt.Tooltip("instrument_label:N", title="Obligatie"),
                alt.Tooltip("event:N", title="Event"),
                alt.Tooltip("transactiebedrag:Q", title="Transactiebedrag", format=",.2f"),
                alt.Tooltip("rente_ontvangen:Q", title="Ontvangen rente", format=",.2f"),
                alt.Tooltip("cum_transactiebedrag:Q", title="Cumulatieve waarde", format=",.2f"),
                alt.Tooltip("price:Q", title="Prijs", format=",.4f"),
                alt.Tooltip("cost:Q", title="Kosten", format=",.2f"),
            ],
        )
    )

    cumulative_line = (
        alt.Chart(events)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("tx_date:T", title="Datum (maand/jaar)", axis=alt.Axis(format="%m/%Y", labelAngle=-45)),
            y=alt.Y("cum_transactiebedrag:Q", title="Cumulatieve waarde"),
            tooltip=[
                alt.Tooltip("tx_date:T", title="Datum"),
                alt.Tooltip("cum_transactiebedrag:Q", title="Cumulatieve waarde", format=",.2f"),
            ],
        )
    )

    zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(strokeDash=[6, 4]).encode(y="y:Q")

    chart = (zero_line + cumulative_line + points).properties(height=360)
    st.altair_chart(chart, use_container_width=True)

    details = events[
        [
            "tx_date",
            "instrument_label",
            "event",
            "transactiebedrag",
            "rente_ontvangen",
            "cum_aankoop",
            "cum_verkoop",
            "cum_aflossing",
            "cum_transactiebedrag",
            "price",
            "cost",
            "reference",
        ]
    ].copy()
    details.columns = [
        "Datum",
        "Obligatie",
        "Event",
        "Transactiebedrag",
        "Ontvangen rente",
        "Cumul aankoop",
        "Cumul verkoop",
        "Cumul aflossing",
        "Cumulatieve waarde",
        "Prijs",
        "Kosten",
        "Referentie",
    ]
    st.dataframe(details, use_container_width=True, hide_index=True)


def show_transactions_overview() -> None:
    st.subheader("Alle transacties (excel stijl)")

    with st.expander("Tijdelijk: database reset", expanded=False):
        st.warning("Verwijdert alle data uit de database (transacties, instrumenten, koersen, FX).")
        confirm_reset = st.checkbox("Ik bevestig dat ik de database wil leegmaken", key="confirm_db_reset")
        if st.button("Database leegmaken", key="reset_db_temp_btn", type="secondary"):
            if not confirm_reset:
                st.info("Vink eerst de bevestiging aan.")
            else:
                try:
                    _reset_database_for_testing()
                    st.success("Database is leeggemaakt.")
                    st.rerun()
                except OSError as exc:
                    _handle_error("Database reset is mislukt.", exc)

    st.markdown("**Import transactiebestand (.csv, ; gescheiden)**")
    uploads = st.file_uploader(
        "Drop transactiebestand(en)",
        type=["csv"],
        accept_multiple_files=True,
        key="transaction_import_upload_overview",
    )
    if uploads and st.button("Importeer bestand(en)", key="import_transactions_btn_overview"):
        totals = {
            "processed": 0,
            "skipped_duplicates": 0,
            "skipped_invalid": 0,
            "created_instruments": 0,
        }
        file_results: list[dict[str, object]] = []
        successful_files = 0

        for upload in uploads:
            summary = _import_uploaded_file(upload)
            file_results.append(
                {
                    "file": getattr(upload, "name", "onbekend"),
                    "summary": summary,
                }
            )
            if summary.get("ok"):
                successful_files += 1
                totals["processed"] += int(summary.get("processed") or 0)
                totals["skipped_duplicates"] += int(summary.get("skipped_duplicates") or 0)
                totals["skipped_invalid"] += int(summary.get("skipped_invalid") or 0)
                totals["created_instruments"] += int(summary.get("created_instruments") or 0)

        if successful_files:
            st.success(
                (
                    f"Bestanden verwerkt: {successful_files}/{len(uploads)} | "
                    f"Verwerkt: {totals['processed']} | "
                    f"Duplicates overgeslagen: {totals['skipped_duplicates']} | "
                    f"Ongeldig overgeslagen: {totals['skipped_invalid']} | "
                    f"Nieuwe instrumenten: {totals['created_instruments']}"
                )
            )
            _reset_runtime_state_and_reload()
            init_state()

        for result in file_results:
            filename = str(result["file"])
            summary = result["summary"]
            if not isinstance(summary, dict):
                st.error(f"{filename}: onbekende importfout")
                continue

            if not summary.get("ok"):
                st.error(f"{filename}: {summary.get('error')}")
                continue

            import_type_label = {
                "transactions": "Transactiebestand",
                "positions": "Positiebestand",
            }.get(str(summary.get("import_type") or ""), "Onbekend")
            st.info(
                (
                    f"{filename} | Type: {import_type_label} | "
                    f"Verwerkt: {summary.get('processed', 0)} | "
                    f"Duplicates: {summary.get('skipped_duplicates', 0)} | "
                    f"Ongeldig: {summary.get('skipped_invalid', 0)} | "
                    f"Nieuwe instrumenten: {summary.get('created_instruments', 0)}"
                )
            )
            details = summary.get("messages", [])
            if details:
                with st.expander(f"Import details - {filename}"):
                    for msg in details:
                        st.write(f"- {msg}")

    tx_df = _db_transactions_dataframe()
    if tx_df.empty:
        st.info("Nog geen transacties in database.")
        return

    tx_df["instrument_label"] = tx_df.apply(
        lambda row: (
            f"{row['instrument_id']} - {row['instrument_name']}"
            if pd.notna(row["instrument_id"]) and str(row["instrument_id"]).strip()
            else "(geen instrument)"
        ),
        axis=1,
    )

    instrument_choices = ["Alle"] + sorted(
        [label for label in tx_df["instrument_label"].dropna().unique().tolist()]
    )
    selected_instrument = st.selectbox("Filter op instrument", instrument_choices)

    filtered_df = tx_df.copy()
    if selected_instrument != "Alle":
        filtered_df = filtered_df[filtered_df["instrument_label"] == selected_instrument].copy()

    editable_columns = [
        "id",
        "tx_date",
        "settlement_date",
        "tx_type",
        "description",
        "account_id",
        "external_account",
        "instrument_id",
        "amount",
        "tx_currency",
        "fx_rate",
        "broker_amount",
        "formula_amount",
        "amount_difference",
        "price",
        "cost",
        "coupon",
        "reference",
    ]
    grid_df = filtered_df[editable_columns].copy()
    grid_df["tx_date"] = pd.to_datetime(grid_df["tx_date"], errors="coerce")
    grid_df["settlement_date"] = pd.to_datetime(grid_df["settlement_date"], errors="coerce")

    edited_df = st.data_editor(
        grid_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True),
            "tx_date": st.column_config.DateColumn("tx_date", format="DD-MM-YYYY"),
            "settlement_date": st.column_config.DateColumn("Valutadatum", format="DD-MM-YYYY"),
            "description": st.column_config.TextColumn("Omschrijving"),
            "external_account": st.column_config.TextColumn("Rekeningnummer", disabled=True),
            "tx_type": st.column_config.SelectboxColumn(
                "tx_type",
                options=["buy", "sell", "aflossing", "coupon", "deposit", "withdrawal"],
            ),
            "fx_rate": st.column_config.NumberColumn("Valutakoers", format="%.6f"),
            "broker_amount": st.column_config.NumberColumn("Broker transactiebedrag", disabled=True, format="%.2f"),
            "formula_amount": st.column_config.NumberColumn("Formule transactiebedrag", disabled=True, format="%.2f"),
            "amount_difference": st.column_config.NumberColumn("Verschil", disabled=True, format="%.2f"),
        },
        key="transactions_editor",
    )

    diff_df = filtered_df.copy()
    diff_df["amount_difference"] = pd.to_numeric(diff_df["amount_difference"], errors="coerce")
    diff_df = diff_df[diff_df["amount_difference"].abs() >= 0.01]
    if not diff_df.empty:
        st.markdown("**Verschillen transactiebedrag (broker vs formule)**")
        diff_show = diff_df[
            [
                "tx_date",
                "tx_type",
                "external_account",
                "instrument_id",
                "reference",
                "broker_amount",
                "formula_amount",
                "amount_difference",
            ]
        ].copy()
        diff_show = _format_date_column(diff_show, "tx_date")
        diff_show.columns = [
            "Boekdatum",
            "Type",
            "Rekeningnummer",
            "ISIN",
            "Referentie",
            "Broker bedrag",
            "Formule bedrag",
            "Verschil",
        ]
        st.dataframe(diff_show, use_container_width=True, hide_index=True)

    delete_candidates = st.multiselect(
        "Markeer transacties voor verwijderen",
        options=grid_df["id"].tolist(),
        help="Soft delete: transacties verdwijnen uit actieve overzichten maar blijven historisch in de database.",
    )

    if st.button("Verwijder geselecteerde transacties", key="delete_tx_rows"):
        if not delete_candidates:
            st.info("Geen transacties geselecteerd.")
        else:
            removed = 0
            for tx_id in delete_candidates:
                try:
                    _db_soft_delete_transaction(int(tx_id))
                    removed += 1
                except (TypeError, ValueError) as exc:
                    _log_event("delete_tx_failed", level="warning", tx_id=tx_id, error=str(exc))
            if removed:
                st.success(f"{removed} transactie(s) verwijderd.")
                _reset_runtime_state_and_reload()
                st.rerun()

    if st.button("Wijzigingen opslaan", key="save_tx_edits"):
        original = grid_df.set_index("id")
        edited = edited_df.set_index("id")
        changed_ids = []

        for tx_id in edited.index:
            if tx_id not in original.index:
                continue
            if not edited.loc[tx_id].equals(original.loc[tx_id]):
                changed_ids.append(tx_id)

        if not changed_ids:
            st.info("Geen wijzigingen gevonden.")
            return

        saved = 0
        errors = []
        for tx_id in changed_ids:
            row_dict = edited.loc[tx_id].to_dict()
            row_dict["id"] = tx_id
            try:
                _db_update_transaction_row(row_dict)
                saved += 1
            except (ValueError, TypeError) as exc:
                errors.append(f"id={tx_id}: {exc}")
                _log_event("update_tx_failed", level="warning", tx_id=tx_id, error=str(exc))

        if saved:
            st.success(f"{saved} wijziging(en) opgeslagen.")
            _reset_runtime_state_and_reload()
            st.rerun()

        if errors:
            st.error("Niet alle wijzigingen konden worden opgeslagen:")
            for msg in errors[:20]:
                st.write(f"- {msg}")


def show_prices_overview() -> None:
    st.subheader("Koersen")

    prices_df = _db_bond_prices_dataframe()
    if prices_df.empty:
        st.info("Nog geen opgeslagen koersen beschikbaar.")
        return

    prices_df["instrument_label"] = prices_df.apply(
        lambda row: (
            f"{row['isin']} - {row['instrument_name']}"
            if pd.notna(row["instrument_name"]) and str(row["instrument_name"]).strip()
            else str(row["isin"])
        ),
        axis=1,
    )
    prices_df["price_date"] = pd.to_datetime(prices_df["price_date"], errors="coerce")

    col1, col2 = st.columns(2)
    instrument_options = ["Alle"] + sorted(prices_df["instrument_label"].dropna().unique().tolist())
    selected_instrument = col1.selectbox("Filter op obligatie", instrument_options)

    currency_options = ["Alle"] + sorted(prices_df["currency"].dropna().astype(str).unique().tolist())
    selected_currency = col2.selectbox("Filter op valuta", currency_options)

    date_min = prices_df["price_date"].dropna().min().date()
    date_max = prices_df["price_date"].dropna().max().date()
    date_start, date_end = st.slider(
        "Datumrange",
        min_value=date_min,
        max_value=date_max,
        value=(date_min, date_max),
        format="DD-MM-YYYY",
        key="prices_date_range",
    )

    sort_col1, sort_col2 = st.columns([3, 1])
    sort_column = sort_col1.selectbox(
        "Sorteer op",
        options=["price_date", "isin", "currency", "price"],
        index=0,
    )
    sort_ascending = sort_col2.checkbox("Oplopend", value=False)

    filtered = prices_df.copy()
    if selected_instrument != "Alle":
        filtered = filtered[filtered["instrument_label"] == selected_instrument].copy()
    if selected_currency != "Alle":
        filtered = filtered[filtered["currency"] == selected_currency].copy()
    filtered = filtered[
        (filtered["price_date"].dt.date >= date_start)
        & (filtered["price_date"].dt.date <= date_end)
    ].copy()

    if filtered.empty:
        st.info("Geen koersen gevonden voor de gekozen filters.")
        return

    filtered = filtered.sort_values(by=sort_column, ascending=sort_ascending)
    display_df = filtered[["price_date", "isin", "instrument_label", "currency", "price"]].copy()
    display_df = _format_date_column(display_df, "price_date")
    display_df.columns = ["Koersdatum", "ISIN", "Obligatie", "Valuta", "Koers"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_bond_maintenance() -> None:
    st.subheader("Onderhoud obligaties")

    rows = _db_load_instruments()
    if not rows:
        st.info("Nog geen obligaties beschikbaar in database.")
        return

    instruments_df = pd.DataFrame([dict(r) for r in rows])
    instruments_df = instruments_df[
        [
            "isin",
            "name",
            "currency",
            "start_date",
            "maturity_date",
            "interest_rate",
            "minimum_purchase_value",
            "smallest_trading_unit",
            "last_price_date",
            "last_price",
        ]
    ].copy()

    filter_value = st.text_input("Filter op ISIN of naam", value="").strip().lower()
    filtered_df = instruments_df.copy()
    if filter_value:
        filtered_df = filtered_df[
            filtered_df["isin"].astype(str).str.lower().str.contains(filter_value)
            | filtered_df["name"].astype(str).str.lower().str.contains(filter_value)
        ].copy()

    filtered_df["start_date"] = pd.to_datetime(filtered_df["start_date"], errors="coerce")
    filtered_df["maturity_date"] = pd.to_datetime(filtered_df["maturity_date"], errors="coerce")
    filtered_df = _format_date_column(filtered_df, "last_price_date")

    if filtered_df.empty:
        st.info("Geen obligaties gevonden voor deze filter.")
        return

    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "isin": st.column_config.TextColumn("ISIN", disabled=True),
            "start_date": st.column_config.DateColumn("Startdatum", format="DD-MM-YYYY"),
            "maturity_date": st.column_config.DateColumn("Einddatum", format="DD-MM-YYYY"),
            "last_price_date": st.column_config.TextColumn("Laatste koersdatum", disabled=True),
            "last_price": st.column_config.NumberColumn("Laatste koers", disabled=True, format="%.6f"),
            "interest_rate": st.column_config.NumberColumn("Coupon/interest rate", format="%.6f"),
            "minimum_purchase_value": st.column_config.NumberColumn("Min. aankoop", format="%.2f"),
            "smallest_trading_unit": st.column_config.NumberColumn("Min. eenheid", format="%d"),
        },
        key="bond_maintenance_editor",
    )

    if st.button("Wijzigingen obligaties opslaan", key="save_bond_maintenance"):
        original = filtered_df.set_index("isin")
        edited = edited_df.set_index("isin")
        changed_isins: list[str] = []

        for isin in edited.index:
            if isin not in original.index:
                continue
            if not edited.loc[isin].equals(original.loc[isin]):
                changed_isins.append(str(isin))

        if not changed_isins:
            st.info("Geen wijzigingen gevonden.")
            return

        saved = 0
        errors: list[str] = []
        for isin in changed_isins:
            row_dict = edited.loc[isin].to_dict()
            row_dict["isin"] = isin
            try:
                _db_update_instrument_row(row_dict)
                saved += 1
            except (TypeError, ValueError) as exc:
                errors.append(f"{isin}: {exc}")

        if saved:
            st.success(f"{saved} obligatie(s) bijgewerkt.")
            _reset_runtime_state_and_reload()
            st.rerun()

        if errors:
            st.error("Niet alle wijzigingen konden worden opgeslagen:")
            for msg in errors[:20]:
                st.write(f"- {msg}")


def _future_coupon_dates(from_date: date, maturity: date, freq_per_year: int) -> list[date]:
    if freq_per_year <= 0:
        freq_per_year = 1
    months = max(1, 12 // freq_per_year)
    dates: list[date] = []
    d = maturity
    while d > from_date:
        dates.append(d)
        d_ts = pd.Timestamp(d) - pd.DateOffset(months=months)
        d = d_ts.date()
    return sorted(dates)


def _estimate_accrued_interest_now(
    as_of: date,
    start_date: date | None,
    maturity_date: date | None,
    outstanding_nominal: float,
    coupon_pct: float,
    freq_per_year: int,
) -> float:
    if (
        outstanding_nominal <= 0
        or coupon_pct <= 0
        or maturity_date is None
        or freq_per_year <= 0
        or as_of >= maturity_date
    ):
        return 0.0

    months = max(1, 12 // freq_per_year)
    next_coupon = maturity_date
    while next_coupon > as_of:
        prev_candidate = (pd.Timestamp(next_coupon) - pd.DateOffset(months=months)).date()
        if prev_candidate <= as_of:
            break
        next_coupon = prev_candidate

    prev_coupon = (pd.Timestamp(next_coupon) - pd.DateOffset(months=months)).date()
    if start_date is not None and prev_coupon < start_date:
        prev_coupon = start_date

    period_days = max(1, (next_coupon - prev_coupon).days)
    elapsed_days = min(period_days, max(0, (as_of - prev_coupon).days))
    accrual_factor = elapsed_days / period_days

    coupon_per_period = outstanding_nominal * (coupon_pct / 100.0) / freq_per_year
    return coupon_per_period * accrual_factor


def show_analysis() -> None:
    st.subheader("Analyse")

    product_collection = st.session_state.product_collection
    if not product_collection.products:
        st.info("Geen obligaties beschikbaar.")
        return

    isin_options = sorted(product_collection.products.keys())
    current_selected = str(st.session_state.get("analysis_selected_isin") or "")
    if current_selected not in isin_options:
        current_selected = isin_options[0]
        st.session_state.analysis_selected_isin = current_selected

    selected_isin = st.selectbox(
        "Kies obligatie",
        options=isin_options,
        key="analysis_selected_isin",
        format_func=lambda isin: f"{isin} - {product_collection.search_product_id(isin).description}",
    )

    product = product_collection.search_product_id(selected_isin)
    obligaties_map = {str(o.get("isin") or ""): o for o in st.session_state.obligaties}
    record = obligaties_map.get(selected_isin, {})

    tx_df = _db_transactions_dataframe()
    bond_tx = tx_df[(tx_df["instrument_id"] == selected_isin) & (tx_df["tx_type"].isin(["buy", "sell", "aflossing", "coupon"]))].copy()
    bond_tx["tx_date"] = pd.to_datetime(bond_tx["tx_date"], errors="coerce")
    bond_tx = bond_tx.dropna(subset=["tx_date"]).sort_values(["tx_date", "id"])

    first_buy = bond_tx[bond_tx["tx_type"] == "buy"].head(1)
    first_buy_date = first_buy["tx_date"].iloc[0].date() if not first_buy.empty else None

    buy_rows = bond_tx[bond_tx["tx_type"] == "buy"].copy()
    buy_rows["amount_num"] = pd.to_numeric(buy_rows["amount"], errors="coerce")
    buy_rows["price_num"] = pd.to_numeric(buy_rows["price"], errors="coerce")
    buy_rows = buy_rows.dropna(subset=["amount_num", "price_num"])

    historical_cost_price_pct = None
    if not buy_rows.empty and float(buy_rows["amount_num"].sum()) > 0:
        weighted_sum = float((buy_rows["amount_num"] * buy_rows["price_num"]).sum())
        weighted_amount = float(buy_rows["amount_num"].sum())
        historical_cost_price_pct = (weighted_sum / weighted_amount) * 100.0
    if historical_cost_price_pct is None:
        historical_cost_price_pct = _to_float(record.get("aankoop_koers_pct"), 100.0)

    start_date = getattr(product, "start_date", None)
    maturity_date = getattr(product, "maturity_date", None)
    coupon_pct = float(getattr(product, "interest_rate", 0.0)) * 100.0
    if coupon_pct == 0:
        coupon_pct = _to_float(record.get("couponrente_pct"), 0.0)
    if pd.isna(coupon_pct):
        coupon_pct = 0.0

    raw_currency = record.get("valuta")
    if pd.isna(raw_currency) or not str(raw_currency).strip() or str(raw_currency).strip().lower() == "nan":
        raw_currency = getattr(product, "issue_currency", None)
    if (raw_currency is None or str(raw_currency).strip().lower() in {"", "nan", "none", "null"}) and not bond_tx.empty:
        tx_currency_series = bond_tx.get("tx_currency")
        if tx_currency_series is not None:
            tx_currency_candidates = tx_currency_series.dropna().astype(str).str.strip()
            tx_currency_candidates = tx_currency_candidates[~tx_currency_candidates.str.lower().isin(["", "nan", "none", "null"])]
            if not tx_currency_candidates.empty:
                raw_currency = tx_currency_candidates.iloc[0]
    currency = _normalize_currency(raw_currency, "EUR")

    ytm_value = None
    if start_date and maturity_date:
        try:
            analysis_bond = PortfolioBond(
                isin=selected_isin,
                naam=getattr(product, "description", selected_isin),
                valuta=currency,
                nominale_waarde=100.0,
                couponrente_pct=coupon_pct,
                aankoop_koers_pct=float(historical_cost_price_pct),
                einddatum=maturity_date,
                settlement_datum=start_date,
                coupon_freq_pa=int(record.get("coupon_freq_pa") or 1),
                berekeningswijze=str(record.get("berekeningswijze") or "ACT/ACT"),
            )
            ytm_raw = analysis_bond.ytm()
            if pd.notna(ytm_raw):
                ytm_value = float(ytm_raw)
        except (TypeError, ValueError):
            ytm_value = None

    prices_df = _db_bond_prices_dataframe()
    prices = prices_df[prices_df["isin"] == selected_isin].copy()
    prices["price_date"] = pd.to_datetime(prices["price_date"], errors="coerce")
    prices = prices.dropna(subset=["price_date"]).sort_values("price_date")
    if first_buy_date is not None:
        prices = prices[prices["price_date"].dt.date >= first_buy_date].copy()

    if currency == "EUR" and not prices.empty:
        price_currency_series = prices.get("currency")
        if price_currency_series is not None:
            price_currency_candidates = price_currency_series.dropna().astype(str).str.strip()
            price_currency_candidates = price_currency_candidates[
                ~price_currency_candidates.str.lower().isin(["", "nan", "none", "null"])
            ]
            if not price_currency_candidates.empty:
                currency = _normalize_currency(price_currency_candidates.iloc[0], "EUR")

    latest_price_pct = float(historical_cost_price_pct)
    if not prices.empty:
        last_price_series = pd.to_numeric(prices["price"], errors="coerce").dropna()
        if not last_price_series.empty:
            latest_price_pct = float(last_price_series.iloc[-1])

    bond_tx["calc_cashflow"] = pd.to_numeric(bond_tx.get("tx_cashflow"), errors="coerce")
    missing_cashflow = bond_tx["calc_cashflow"].isna()
    if missing_cashflow.any():
        legacy_tx = bond_tx[missing_cashflow].copy()
        legacy_tx["calc_cashflow"] = legacy_tx.apply(
            lambda row: _derive_tx_cashflow(
                str(row.get("tx_type") or ""),
                _coerce_optional_float(row.get("amount"), "amount"),
                _coerce_optional_float(row.get("price"), "price"),
                _coerce_optional_float(row.get("cost"), "cost"),
                _coerce_optional_float(row.get("coupon"), "coupon"),
            ),
            axis=1,
        )
        bond_tx.loc[missing_cashflow, "calc_cashflow"] = legacy_tx["calc_cashflow"].values
    bond_tx["calc_cashflow"] = bond_tx["calc_cashflow"].fillna(0.0)

    buy_nominal = float(bond_tx.loc[bond_tx["tx_type"] == "buy", "amount"].fillna(0.0).sum())
    sell_nominal = float(bond_tx.loc[bond_tx["tx_type"] == "sell", "amount"].fillna(0.0).sum())
    redemption_nominal = float(bond_tx.loc[bond_tx["tx_type"] == "aflossing", "amount"].fillna(0.0).sum())
    outstanding_nominal = buy_nominal - sell_nominal - redemption_nominal

    buy_cost_price = abs(float(pd.to_numeric(bond_tx.loc[bond_tx["tx_type"] == "buy", "calc_cashflow"], errors="coerce").fillna(0.0).sum()))
    received_coupon_total = float(pd.to_numeric(bond_tx.loc[bond_tx["tx_type"] == "coupon", "calc_cashflow"], errors="coerce").fillna(0.0).sum())

    last_known_date = date.today()
    if not bond_tx.empty:
        last_known_date = max(last_known_date, bond_tx["tx_date"].max().date())

    freq = int(record.get("coupon_freq_pa") or 1)
    coupon_dates = _future_coupon_dates(last_known_date, maturity_date, freq) if maturity_date else []
    remaining_coupon_total = 0.0
    redemption_at_maturity = 0.0
    if outstanding_nominal > 0 and maturity_date:
        coupon_amount = outstanding_nominal * (coupon_pct / 100.0) / max(freq, 1)
        remaining_coupon_total = coupon_amount * len(coupon_dates)
        redemption_at_maturity = outstanding_nominal

    if pd.isna(remaining_coupon_total):
        remaining_coupon_total = 0.0
    if pd.isna(redemption_at_maturity):
        redemption_at_maturity = 0.0

    today = date.today()
    discount_rate_pct = st.slider(
        "Discount % (contant maken naar vandaag)",
        min_value=0.0,
        max_value=15.0,
        value=3.0,
        step=0.1,
        format="%.1f%%",
        key="analysis_discount_rate",
    )
    discount_rate = discount_rate_pct / 100.0

    accrued_interest_now = _estimate_accrued_interest_now(
        as_of=today,
        start_date=start_date,
        maturity_date=maturity_date,
        outstanding_nominal=max(0.0, outstanding_nominal),
        coupon_pct=coupon_pct,
        freq_per_year=max(freq, 1),
    )

    def _net_sale_value(price_pct: float) -> float:
        gross = (max(0.0, outstanding_nominal) * (price_pct / 100.0)) + accrued_interest_now
        tx_cost = gross * 0.001
        return gross - tx_cost

    def _discount_to_today(amount: float, flow_date: date) -> float:
        if flow_date <= today:
            return amount
        years = (flow_date - today).days / 365.0
        return amount / ((1.0 + discount_rate) ** years)

    historical_basis_amount = max(0.0, outstanding_nominal) * (historical_cost_price_pct / 100.0)
    if historical_basis_amount <= 0:
        historical_basis_amount = buy_cost_price

    historical_basis_today = _discount_to_today(historical_basis_amount, today)
    received_coupon_today = _discount_to_today(received_coupon_total, today)

    sell_prices = [latest_price_pct - 0.5, latest_price_pct, latest_price_pct + 0.5]
    scenario_rows: list[dict[str, object]] = []
    for price_pct in sell_prices:
        net_sale = _net_sale_value(price_pct)
        sale_today = _discount_to_today(net_sale, today)
        total_value_today = received_coupon_today + sale_today
        result_amount = total_value_today - historical_basis_today
        result_pct = (result_amount / historical_basis_today * 100.0) if historical_basis_today else 0.0
        label = f"Verkoop nu @ {price_pct:,.2f}%"
        calc_text = (
            "Uitkomst % = ((Ontvangen coupons (PV vandaag) + Verkoopopbrengst nu netto - Historische kostprijs (PV vandaag)) "
            "/ Historische kostprijs (PV vandaag)) * 100"
        )
        scenario_rows.append(
            {
                "Scenario": label,
                "Koers %": round(price_pct, 3),
                "Uitkomst %": round(result_pct, 3),
                "Ontvangen coupons (PV vandaag)": round(received_coupon_today, 6),
                "Verkoopopbrengst nu netto": round(sale_today, 6),
                "Historische kostprijs (PV vandaag)": round(historical_basis_today, 6),
                "Exacte berekening": calc_text,
            }
        )

    hold_pv = 0.0
    future_coupon_dates = _future_coupon_dates(today, maturity_date, freq) if maturity_date else []
    if max(0.0, outstanding_nominal) > 0 and maturity_date:
        coupon_amount = outstanding_nominal * (coupon_pct / 100.0) / max(freq, 1)
        for coupon_date in future_coupon_dates:
            hold_pv += _discount_to_today(coupon_amount, coupon_date)
        hold_pv += _discount_to_today(outstanding_nominal, maturity_date)

    hold_total_value_today = received_coupon_today + hold_pv
    hold_result_amount = hold_total_value_today - historical_basis_today
    hold_result_pct = (hold_result_amount / historical_basis_today * 100.0) if historical_basis_today else 0.0
    hold_calc_text = (
        "Uitkomst % = ((Ontvangen coupons (PV vandaag) + PV toekomstige coupons + PV aflossing - Historische kostprijs (PV vandaag)) "
        "/ Historische kostprijs (PV vandaag)) * 100"
    )
    scenario_rows.append(
        {
            "Scenario": "Aanhouden tot aflossing (100%)",
            "Koers %": 100.0,
            "Uitkomst %": round(hold_result_pct, 3),
            "Ontvangen coupons (PV vandaag)": round(received_coupon_today, 6),
            "Verkoopopbrengst nu netto": round(hold_pv, 6),
            "Historische kostprijs (PV vandaag)": round(historical_basis_today, 6),
            "Exacte berekening": hold_calc_text,
        }
    )

    left, right = st.columns(2)
    with right:
        st.markdown("**Basiscijfers**")
        details_rows = [
            {"Veld": "Open nominale positie", "Waarde": f"{outstanding_nominal:,.2f}"},
            {"Veld": "Laatste koers", "Waarde": f"{latest_price_pct:,.3f}%"},
            {"Veld": "Historische kostprijs %", "Waarde": f"{historical_cost_price_pct:,.3f}%"},
            {"Veld": "Historische kostprijs bedrag", "Waarde": f"{currency} {historical_basis_amount:,.2f}"},
            {"Veld": "Ontvangen coupons", "Waarde": f"{currency} {received_coupon_total:,.2f}"},
            {"Veld": "Meeverkochte rente (nu)", "Waarde": f"{currency} {accrued_interest_now:,.2f}"},
            {"Veld": "Discount %", "Waarde": f"{discount_rate_pct:,.2f}%"},
            {"Veld": "Startdatum", "Waarde": _format_date_display(start_date) if start_date else "-"},
            {"Veld": "Einddatum", "Waarde": _format_date_display(maturity_date) if maturity_date else "-"},
            {"Veld": "Coupon %", "Waarde": f"{coupon_pct:,.3f}%"},
            {"Veld": "Valuta", "Waarde": currency},
            {"Veld": "YTM", "Waarde": f"{ytm_value:,.3f}%" if ytm_value is not None else "-"},
        ]
        st.dataframe(pd.DataFrame(details_rows), use_container_width=True, hide_index=True)

    with left:
        st.markdown("**Koersontwikkeling**")
        if prices.empty:
            st.info("Geen koersdata beschikbaar voor deze obligatie.")
        else:
            y_values = prices["price"].astype(float).tolist() + [float(historical_cost_price_pct)]
            y_min = min(y_values)
            y_max = max(y_values)
            if y_max > y_min:
                padding = (y_max - y_min) * 0.12
            else:
                padding = max(abs(y_max) * 0.02, 0.01)
            y_domain = [y_min - padding, y_max + padding]

            base_chart = alt.Chart(prices)
            koers_line = base_chart.mark_line(strokeWidth=2).encode(
                x=alt.X("price_date:T", title="Datum", axis=alt.Axis(format="%m/%Y", labelAngle=-45)),
                y=alt.Y(
                    "price:Q",
                    title=f"Koers ({currency})",
                    scale=alt.Scale(zero=False, domain=y_domain),
                ),
            )
            koers_points = base_chart.mark_point(size=45, filled=True).encode(
                x=alt.X("price_date:T", title="Datum", axis=alt.Axis(format="%m/%Y", labelAngle=-45)),
                y=alt.Y("price:Q", scale=alt.Scale(zero=False, domain=y_domain)),
                tooltip=[
                    alt.Tooltip("price_date:T", title="Datum"),
                    alt.Tooltip("price:Q", title="Koers", format=",.4f"),
                ],
            )
            purchase_df = pd.DataFrame(
                {
                    "price_date": [prices["price_date"].min(), prices["price_date"].max()],
                    "purchase_price": [historical_cost_price_pct, historical_cost_price_pct],
                }
            )
            purchase_line = alt.Chart(purchase_df).mark_line(strokeDash=[6, 4]).encode(
                x=alt.X("price_date:T", axis=alt.Axis(format="%m/%Y", labelAngle=-45)),
                y=alt.Y("purchase_price:Q", scale=alt.Scale(zero=False, domain=y_domain)),
                tooltip=[alt.Tooltip("purchase_price:Q", title="Historische kostprijs", format=",.4f")],
            )
            st.altair_chart((koers_line + koers_points + purchase_line).properties(height=320), use_container_width=True)

    st.markdown("**Scenariovergelijking (compact)**")
    scenario_raw_df = pd.DataFrame(scenario_rows)
    scenario_df = scenario_raw_df[["Scenario", "Koers %", "Uitkomst %"]].copy()
    scenario_df["Koers %"] = scenario_df["Koers %"].map(lambda value: f"{value:,.3f}%")
    scenario_df["Uitkomst %"] = scenario_df["Uitkomst %"].map(lambda value: f"{value:,.3f}%")
    st.dataframe(scenario_df, use_container_width=True, hide_index=True)

    hover_df = scenario_raw_df.copy()
    hover_df["Uitkomst_label"] = hover_df["Uitkomst %"].map(lambda value: f"{value:,.3f}%")
    hover_chart_base = alt.Chart(hover_df).encode(
        x=alt.X("Scenario:N", title="Scenario"),
        y=alt.Y("Uitkomst %:Q", title="Uitkomst %"),
        tooltip=[
            alt.Tooltip("Scenario:N", title="Scenario"),
            alt.Tooltip("Koers %:Q", title="Koers %", format=".3f"),
            alt.Tooltip("Uitkomst %:Q", title="Uitkomst %", format=".3f"),
            alt.Tooltip("Ontvangen coupons (PV vandaag):Q", title="Ontvangen coupons (PV)", format=",.6f"),
            alt.Tooltip("Verkoopopbrengst nu netto:Q", title="Scenario-opbrengst component", format=",.6f"),
            alt.Tooltip("Historische kostprijs (PV vandaag):Q", title="Historische kostprijs (PV)", format=",.6f"),
            alt.Tooltip("Exacte berekening:N", title="Exacte berekening"),
        ],
    )
    hover_points = hover_chart_base.mark_point(size=180, filled=True)
    hover_labels = hover_chart_base.mark_text(dy=-10).encode(text=alt.Text("Uitkomst_label:N"))
    st.altair_chart((hover_points + hover_labels).properties(height=260), use_container_width=True)

    st.markdown("**Bekende transacties**")
    if bond_tx.empty:
        st.info("Geen bekende transacties voor dit instrument.")
    else:
        tx_display = bond_tx[["tx_date", "tx_type", "amount", "tx_cashflow", "tx_currency", "price", "reference"]].copy()
        tx_display = _format_date_column(tx_display, "tx_date")
        tx_display.columns = ["Datum", "Type", "Nominaal", "Transactiebedrag", "Valuta", "Prijs", "Referentie"]
        st.dataframe(tx_display, use_container_width=True, hide_index=True)

    st.markdown("**Geprojecteerde toekomstige transacties**")
    if maturity_date is None:
        st.info("Geen einddatum beschikbaar om projecties te maken.")
        return

    projected_rows: list[dict[str, object]] = []
    if outstanding_nominal > 0 and coupon_dates:
        coupon_amount = outstanding_nominal * (coupon_pct / 100.0) / max(freq, 1)
        for d in coupon_dates:
            projected_rows.append(
                {
                    "Datum": d,
                    "Type": "coupon",
                    "Bedrag": coupon_amount,
                    "Valuta": currency,
                }
            )
        projected_rows.append(
            {
                "Datum": maturity_date,
                "Type": "aflossing",
                "Bedrag": outstanding_nominal,
                "Valuta": currency,
            }
        )

    if not projected_rows:
        st.info("Geen toekomstige projecties beschikbaar (mogelijk geen open nominale positie).")
    else:
        projected_df = pd.DataFrame(projected_rows).sort_values(["Datum", "Type"])
        projected_df = _format_date_column(projected_df, "Datum")
        st.dataframe(projected_df, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Bond Portfolio MVP", layout="wide")
    st.title("Bond Portfolio MVP")

    st.markdown(
        """
        <style>
        [data-testid="stDataFrame"] {
            transform: none !important;
            filter: none !important;
            backface-visibility: hidden;
        }
        [data-testid="stDataFrame"] * {
            -webkit-font-smoothing: antialiased !important;
            -moz-osx-font-smoothing: grayscale !important;
            text-rendering: geometricPrecision !important;
        }
        [data-testid="stDataFrame"] canvas {
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    init_state()

    view = st.sidebar.radio(
        "Navigatie",
        ["Transactie-overzicht", "Obligatie-tijdlijn", "Koersen", "Analyse", "Onderhoud obligaties"],
    )

    if view == "Transactie-overzicht":
        show_transactions_overview()
    elif view == "Obligatie-tijdlijn":
        show_bond_timeline()
    elif view == "Koersen":
        show_prices_overview()
    elif view == "Analyse":
        show_analysis()
    else:
        show_bond_maintenance()


if __name__ == "__main__":
    main()
