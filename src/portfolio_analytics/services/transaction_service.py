"""
Transaction engine — executes buy, sell, FX, fee, and interest operations.

Settlement rules:
    • If the instrument's currency matches a cash account in the portfolio,
      settle in that currency.
    • Otherwise convert via FX into the portfolio's base currency (EUR).

Every operation creates one or more ``Transaction`` records in the ledger.
Cash balances are always *derived* by summing transactions — the engine
never stores a mutable balance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from portfolio_analytics.domain.enums import TransactionType
from portfolio_analytics.domain.interfaces import FXServiceBase, TransactionServiceBase
from portfolio_analytics.domain.models import CashAccount, Transaction
from portfolio_analytics.repositories.base import (
    CashAccountRepository,
    InstrumentRepository,
    PortfolioRepository,
    TransactionRepository,
)


def _new_id() -> str:
    return str(uuid.uuid4())


class TransactionService(TransactionServiceBase):
    """
    Concrete transaction engine backed by repository persistence.

    Raises ``ValueError`` when:
        • The portfolio or instrument does not exist.
        • Insufficient cash for a buy order.
        • Insufficient position for a sell order.
    """

    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        instrument_repo: InstrumentRepository,
        cash_account_repo: CashAccountRepository,
        transaction_repo: TransactionRepository,
        fx_service: FXServiceBase,
    ) -> None:
        self._portfolios = portfolio_repo
        self._instruments = instrument_repo
        self._cash_accounts = cash_account_repo
        self._transactions = transaction_repo
        self._fx = fx_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_buy(
        self,
        portfolio_id: str,
        instrument_id: str,
        quantity: float,
        price: float,
        timestamp: datetime,
    ) -> Transaction:
        portfolio = self._require_portfolio(portfolio_id)
        instrument = self._require_instrument(instrument_id)

        settlement_ccy = self._resolve_settlement_currency(
            portfolio_id, instrument.currency, portfolio.base_currency
        )
        fx_rate = self._fx.get_fx_rate(
            instrument.currency, settlement_ccy, timestamp.date()
        )
        amount = round(quantity * price * fx_rate, 2)

        # Check cash sufficiency
        balance = self._cash_balance(portfolio_id, settlement_ccy, timestamp)
        if balance < amount:
            raise ValueError(
                f"Insufficient cash: need {amount:.2f} {settlement_ccy}, "
                f"have {balance:.2f}"
            )

        tx = Transaction(
            id=_new_id(),
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            type=TransactionType.BUY,
            quantity=quantity,
            price=price,
            amount=-amount,  # cash outflow
            currency=settlement_ccy,
            timestamp=timestamp,
            metadata={"fx_rate": fx_rate, "instrument_currency": instrument.currency},
        )
        self._transaction_repo_save(tx)
        return tx

    def execute_sell(
        self,
        portfolio_id: str,
        instrument_id: str,
        quantity: float,
        price: float,
        timestamp: datetime,
    ) -> Transaction:
        portfolio = self._require_portfolio(portfolio_id)
        instrument = self._require_instrument(instrument_id)

        # Check position sufficiency
        position = self._position(portfolio_id, instrument_id, timestamp)
        if position < quantity:
            raise ValueError(
                f"Insufficient position: need {quantity}, have {position}"
            )

        settlement_ccy = self._resolve_settlement_currency(
            portfolio_id, instrument.currency, portfolio.base_currency
        )
        fx_rate = self._fx.get_fx_rate(
            instrument.currency, settlement_ccy, timestamp.date()
        )
        amount = round(quantity * price * fx_rate, 2)

        tx = Transaction(
            id=_new_id(),
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            type=TransactionType.SELL,
            quantity=quantity,
            price=price,
            amount=amount,  # cash inflow
            currency=settlement_ccy,
            timestamp=timestamp,
            metadata={"fx_rate": fx_rate, "instrument_currency": instrument.currency},
        )
        self._transaction_repo_save(tx)
        return tx

    def execute_fx(
        self,
        portfolio_id: str,
        from_currency: str,
        to_currency: str,
        amount: float,
        rate: float,
        timestamp: datetime,
    ) -> tuple[Transaction, Transaction]:
        self._require_portfolio(portfolio_id)

        # Ensure cash accounts exist
        self._ensure_cash_account(portfolio_id, from_currency)
        self._ensure_cash_account(portfolio_id, to_currency)

        balance = self._cash_balance(portfolio_id, from_currency, timestamp)
        if balance < amount:
            raise ValueError(
                f"Insufficient {from_currency}: need {amount:.2f}, have {balance:.2f}"
            )

        pair_id = _new_id()
        converted = round(amount * rate, 2)

        tx_debit = Transaction(
            id=_new_id(),
            portfolio_id=portfolio_id,
            instrument_id=None,
            type=TransactionType.FX,
            quantity=amount,
            price=rate,
            amount=-amount,
            currency=from_currency,
            timestamp=timestamp,
            metadata={"fx_pair_id": pair_id, "direction": "debit"},
        )
        tx_credit = Transaction(
            id=_new_id(),
            portfolio_id=portfolio_id,
            instrument_id=None,
            type=TransactionType.FX,
            quantity=converted,
            price=1.0 / rate if rate else 0,
            amount=converted,
            currency=to_currency,
            timestamp=timestamp,
            metadata={"fx_pair_id": pair_id, "direction": "credit"},
        )
        self._transaction_repo_save(tx_debit)
        self._transaction_repo_save(tx_credit)
        return tx_debit, tx_credit

    def execute_fee(
        self,
        portfolio_id: str,
        amount: float,
        currency: str,
        timestamp: datetime,
        instrument_id: Optional[str] = None,
    ) -> Transaction:
        """Debit a fee from the portfolio's cash account."""
        self._require_portfolio(portfolio_id)
        tx = Transaction(
            id=_new_id(),
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            type=TransactionType.FEE,
            quantity=0,
            price=0,
            amount=-abs(amount),
            currency=currency,
            timestamp=timestamp,
        )
        self._transaction_repo_save(tx)
        return tx

    def execute_interest(
        self,
        portfolio_id: str,
        amount: float,
        currency: str,
        timestamp: datetime,
        instrument_id: Optional[str] = None,
    ) -> Transaction:
        """Credit an interest/coupon payment to the portfolio."""
        self._require_portfolio(portfolio_id)
        tx = Transaction(
            id=_new_id(),
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            type=TransactionType.INTEREST,
            quantity=0,
            price=0,
            amount=abs(amount),
            currency=currency,
            timestamp=timestamp,
        )
        self._transaction_repo_save(tx)
        return tx

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_portfolio(self, portfolio_id: str):
        p = self._portfolios.get(portfolio_id)
        if p is None:
            raise ValueError(f"Portfolio not found: {portfolio_id}")
        return p

    def _require_instrument(self, instrument_id: str):
        i = self._instruments.get(instrument_id)
        if i is None:
            raise ValueError(f"Instrument not found: {instrument_id}")
        return i

    def _resolve_settlement_currency(
        self, portfolio_id: str, instrument_ccy: str, base_ccy: str
    ) -> str:
        """Use the instrument's currency if the portfolio has a matching account."""
        acct = self._cash_accounts.find_by_portfolio_and_currency(
            portfolio_id, instrument_ccy
        )
        if acct is not None:
            return instrument_ccy
        return base_ccy

    def _ensure_cash_account(self, portfolio_id: str, currency: str) -> CashAccount:
        acct = self._cash_accounts.find_by_portfolio_and_currency(
            portfolio_id, currency
        )
        if acct is None:
            acct = CashAccount(id=_new_id(), portfolio_id=portfolio_id, currency=currency)
            self._cash_accounts.save(acct)
        return acct

    def _cash_balance(
        self, portfolio_id: str, currency: str, as_of: datetime
    ) -> float:
        """Derive cash balance by summing transaction amounts in *currency*."""
        txs = self._transactions.list_by_portfolio(portfolio_id, up_to=as_of)
        return sum(tx.amount for tx in txs if tx.currency == currency)

    def _position(
        self, portfolio_id: str, instrument_id: str, as_of: datetime
    ) -> float:
        """Derive security position from buy/sell transactions."""
        txs = self._transactions.list_by_portfolio(portfolio_id, up_to=as_of)
        qty = 0.0
        for tx in txs:
            if tx.instrument_id != instrument_id:
                continue
            if tx.type == TransactionType.BUY:
                qty += tx.quantity
            elif tx.type == TransactionType.SELL:
                qty -= tx.quantity
        return qty

    def _transaction_repo_save(self, tx: Transaction) -> None:
        self._transactions.save(tx)
