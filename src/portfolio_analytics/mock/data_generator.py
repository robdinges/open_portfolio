"""
Deterministic mock data generator.

``generate_portfolio`` creates a fully populated portfolio with:
    • 5–10 instruments (mix of stocks and bonds in 1–2 currencies)
    • 1 client, 1 portfolio, matching cash accounts
    • 100–300 transactions spread over a realistic timespan

Randomness is seeded from the ``portfolio_id`` so that the same ID always
produces the identical dataset — useful for reproducible demos and tests.
"""

from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timedelta

from portfolio_analytics.domain.enums import InstrumentType, TransactionType
from portfolio_analytics.domain.models import (
    CashAccount,
    Client,
    Instrument,
    Portfolio,
    Transaction,
)

# ---------------------------------------------------------------------------
# Instrument templates
# ---------------------------------------------------------------------------

_STOCK_TEMPLATES = [
    ("Apple Inc.", "USD"),
    ("Microsoft Corp.", "USD"),
    ("Alphabet Inc.", "USD"),
    ("Amazon.com Inc.", "USD"),
    ("ASML Holding", "EUR"),
    ("SAP SE", "EUR"),
    ("TotalEnergies SE", "EUR"),
    ("Nestlé SA", "CHF"),
    ("HSBC Holdings", "GBP"),
    ("Unilever PLC", "GBP"),
]

_BOND_TEMPLATES = [
    ("German Bund 2.5% 2034", "EUR", 2.5),
    ("French OAT 3.0% 2033", "EUR", 3.0),
    ("US Treasury 4.25% 2032", "USD", 4.25),
    ("UK Gilt 3.75% 2035", "GBP", 3.75),
    ("Netherlands 2.0% 2030", "EUR", 2.0),
    ("Austria 2.75% 2031", "EUR", 2.75),
]


def _make_seed(portfolio_id: str) -> int:
    return int(hashlib.sha256(portfolio_id.encode()).hexdigest(), 16) % (2**32)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_portfolio(
    portfolio_id: str = "demo-portfolio-1",
    client_name: str = "Demo Client",
) -> dict:
    """
    Generate a complete mock dataset for one portfolio.

    Returns a dict with keys:
        ``client``, ``portfolio``, ``instruments``, ``cash_accounts``,
        ``transactions``

    All content is deterministic — the same *portfolio_id* always yields
    identical output.
    """
    rng = random.Random(_make_seed(portfolio_id))

    client_id = str(uuid.UUID(int=rng.getrandbits(128)))
    client = Client(id=client_id, name=client_name)

    portfolio = Portfolio(
        id=portfolio_id,
        name=f"Portfolio {portfolio_id[-4:]}",
        client_id=client_id,
        base_currency="EUR",
    )

    # Pick instruments -------------------------------------------------
    n_stocks = rng.randint(3, 6)
    n_bonds = rng.randint(2, 4)
    stock_picks = rng.sample(_STOCK_TEMPLATES, min(n_stocks, len(_STOCK_TEMPLATES)))
    bond_picks = rng.sample(_BOND_TEMPLATES, min(n_bonds, len(_BOND_TEMPLATES)))

    instruments: list[Instrument] = []
    for i, (name, ccy) in enumerate(stock_picks, start=1):
        instruments.append(
            Instrument(
                id=f"STK-{portfolio_id[-4:]}-{i:03d}",
                name=name,
                type=InstrumentType.STOCK,
                currency=ccy,
                metadata={"sector": "Technology" if "tech" in name.lower() else "General"},
            )
        )
    for i, (name, ccy, coupon) in enumerate(bond_picks, start=1):
        instruments.append(
            Instrument(
                id=f"BND-{portfolio_id[-4:]}-{i:03d}",
                name=name,
                type=InstrumentType.BOND,
                currency=ccy,
                metadata={
                    "coupon_rate": coupon,
                    "maturity_year": 2030 + rng.randint(0, 5),
                },
            )
        )

    # Determine currencies in play ------------------------------------
    currencies = sorted({inst.currency for inst in instruments} | {"EUR"})
    cash_accounts = [
        CashAccount(
            id=f"CA-{portfolio_id[-4:]}-{ccy}",
            portfolio_id=portfolio_id,
            currency=ccy,
        )
        for ccy in currencies
    ]

    # Generate transactions --------------------------------------------
    n_transactions = rng.randint(100, 300)
    start_date = datetime(2024, 1, 2, 9, 0, 0)
    transactions: list[Transaction] = []

    # Seed initial cash deposits
    for ca in cash_accounts:
        deposit_amount = rng.uniform(50_000, 200_000)
        transactions.append(
            Transaction(
                id=str(uuid.UUID(int=rng.getrandbits(128))),
                portfolio_id=portfolio_id,
                instrument_id=None,
                type=TransactionType.INTEREST,  # initial deposit modelled as inflow
                quantity=0,
                price=0,
                amount=round(deposit_amount, 2),
                currency=ca.currency,
                timestamp=start_date,
                metadata={"note": "Initial cash deposit"},
            )
        )

    # ongoing trades
    current_date = start_date + timedelta(days=1)
    positions: dict[str, float] = {}  # instrument_id → quantity held

    for _ in range(n_transactions):
        # advance 1–5 business days
        skip = rng.randint(1, 5)
        for _ in range(skip):
            current_date += timedelta(days=1)
            while current_date.weekday() >= 5:
                current_date += timedelta(days=1)

        inst = rng.choice(instruments)
        held = positions.get(inst.id, 0.0)

        # decide action
        if held > 0 and rng.random() < 0.3:
            tx_type = TransactionType.SELL
        else:
            tx_type = TransactionType.BUY

        if inst.type == InstrumentType.BOND:
            quantity = rng.choice([1000, 2000, 5000, 10000])
            price = round(rng.uniform(95, 105), 2)
        else:
            quantity = rng.randint(1, 50)
            price = round(rng.uniform(20, 500), 2)

        if tx_type == TransactionType.SELL:
            quantity = min(quantity, held)
            if quantity <= 0:
                tx_type = TransactionType.BUY
                quantity = rng.randint(1, 50) if inst.type == InstrumentType.STOCK else rng.choice([1000, 5000])

        amount = round(quantity * price, 2)
        if tx_type == TransactionType.BUY:
            positions[inst.id] = held + quantity
            amount = -amount  # cash outflow
        else:
            positions[inst.id] = held - quantity

        transactions.append(
            Transaction(
                id=str(uuid.UUID(int=rng.getrandbits(128))),
                portfolio_id=portfolio_id,
                instrument_id=inst.id,
                type=tx_type,
                quantity=quantity,
                price=price,
                amount=amount,
                currency=inst.currency,
                timestamp=current_date,
                metadata={},
            )
        )

        # occasional fee
        if rng.random() < 0.15:
            fee = round(abs(amount) * 0.001, 2)
            transactions.append(
                Transaction(
                    id=str(uuid.UUID(int=rng.getrandbits(128))),
                    portfolio_id=portfolio_id,
                    instrument_id=inst.id,
                    type=TransactionType.FEE,
                    quantity=0,
                    price=0,
                    amount=-fee,
                    currency=inst.currency,
                    timestamp=current_date,
                    metadata={"related_trade": transactions[-1].id},
                )
            )

        # occasional interest/coupon
        if inst.type == InstrumentType.BOND and rng.random() < 0.05:
            coupon = round(
                positions.get(inst.id, 0)
                * inst.metadata.get("coupon_rate", 2.5)
                / 100
                / 2,
                2,
            )
            if coupon > 0:
                transactions.append(
                    Transaction(
                        id=str(uuid.UUID(int=rng.getrandbits(128))),
                        portfolio_id=portfolio_id,
                        instrument_id=inst.id,
                        type=TransactionType.INTEREST,
                        quantity=0,
                        price=0,
                        amount=coupon,
                        currency=inst.currency,
                        timestamp=current_date,
                        metadata={"note": "Semi-annual coupon"},
                    )
                )

    return {
        "client": client,
        "portfolio": portfolio,
        "instruments": instruments,
        "cash_accounts": cash_accounts,
        "transactions": sorted(transactions, key=lambda t: t.timestamp),
    }
