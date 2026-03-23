from __future__ import annotations
from datetime import date
from typing import List, Dict
import logging

from .enums import MovementType, TransactionTemplate
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .accounts import CashAccount, Portfolio
from .products import Product


def _ensure_int(val):
    # avoid importing CashAccount at runtime to break circular dependency
    from .accounts import CashAccount

    return val.cash_account_id if isinstance(val, CashAccount) else int(val)


class CashMovement:
    def __init__(
        self,
        transaction: "Transaction",
        amount_account_currency: float,
        amount_original_currency: float,
        movement_type: MovementType,
        transaction_number: int,
        transaction_currency: str,
        exchange_rate: float = 1.0,
    ):
        self.cash_account_id = _ensure_int(transaction.account_id)
        self.portfolio_id = transaction.portfolio_id
        self.transaction_date = transaction.transaction_date
        self.amount_account_currency = amount_account_currency
        self.amount_original_currency = amount_original_currency
        self.movement_type = movement_type
        self.transaction_number = transaction_number
        self.exchange_rate = exchange_rate
        self.transaction_currency = transaction_currency

    def to_dict(self) -> Dict:
        return {
            "cash_account_id": self.cash_account_id,
            "amount": self.amount_account_currency,
            "currency": self.transaction_currency,
            "type": self.movement_type.value,
        }


class SecurityMovement:
    def __init__(
        self,
        transaction: "Transaction",
        product_id: int,
        amount_nominal: float,
        price: float,
        movement_type: MovementType,
    ):
        self.movement_type = movement_type
        self.product_id = product_id
        self.account_id = transaction.account_id
        self.portfolio_id = transaction.portfolio_id
        self.amount_nominal = amount_nominal
        self.price = price
        self.transaction_number = transaction.transaction_number
        self.transaction_date = transaction.transaction_date

    def to_dict(self) -> Dict:
        return {
            "product_id": self.product_id,
            "amount_nominal": self.amount_nominal,
            "price": self.price,
            "type": self.movement_type.value,
        }


class Transaction:
    _counter = 0

    def __init__(
        self,
        transaction_date: date,
        portfolio_id: int,
        account_id: int,
        transaction_currency: str,
    ):
        type(self)._counter += 1
        self.transaction_number = type(self)._counter
        self.transaction_date = transaction_date
        self.portfolio_id = portfolio_id
        self.account_id = account_id
        self.transaction_currency = transaction_currency
        self.cash_movements: List[CashMovement] = []
        self.security_movements: List[SecurityMovement] = []
        logging.info("Created transaction %s", self.transaction_number)

    def add_cash_movement(self, movement: CashMovement):
        if movement not in self.cash_movements:
            self.cash_movements.append(movement)

    def add_security_movement(self, movement: SecurityMovement):
        if movement not in self.security_movements:
            self.security_movements.append(movement)

    def to_dict(self) -> Dict:
        return {
            "transaction_number": self.transaction_number,
            "transaction_date": self.transaction_date,
            "portfolio_id": self.portfolio_id,
            "account_id": self.account_id,
            "transaction_currency": self.transaction_currency,
            "cash_movements": [cm.to_dict() for cm in self.cash_movements],
            "security_movements": [sm.to_dict() for sm in self.security_movements],
        }

    def validate(self, portfolio: Portfolio, product_collection) -> (bool, List[str]):
        # simplified; reuse earlier validation logic if needed
        messages: List[str] = []
        # placeholder: always valid
        return True, messages


class TransactionManager:
    """Factory/utility class for creating and executing transactions."""

    def __init__(self):
        self.history: List[Transaction] = []
        self.templates = {
            TransactionTemplate.BUY: self._buy_template,
            TransactionTemplate.SELL: self._sell_template,
            TransactionTemplate.DEPOSIT: self._deposit_template,
            TransactionTemplate.DIVIDEND: self._dividend_template,
        }

    def _calculate_cost(self, amount: float, price: float) -> float:
        return 0.01 * amount * price

    def _buy_template(
        self,
        transaction_date,
        portfolio_id,
        account_id,
        portfolio,
        product_collection,
        product_id,
        amount,
        price,
        cost=None,
        exchange_rate=1.0,
        transaction_currency=None,
    ):
        if cost is None:
            cost = self._calculate_cost(amount, price)
        product = product_collection.search_product_id(product_id)
        if product is None:
            raise ValueError("Product not found")
        tx = Transaction(transaction_date, portfolio_id, account_id, portfolio.default_currency)
        sm = SecurityMovement(tx, product_id, amount, price, MovementType.SECURITY_BUY)
        tx.add_security_movement(sm)
        # compute amounts in the account's currency
        acct_curr = transaction_currency or product.issue_currency
        amt_original = -amount * price
        amt_account = amt_original * exchange_rate
        total = CashMovement(
            tx,
            amt_account,
            amt_original,
            MovementType.SECURITY_BUY,
            tx.transaction_number,
            acct_curr,
            exchange_rate,
        )
        tx.add_cash_movement(total)
        fee = CashMovement(
            tx,
            -cost * exchange_rate,
            -cost,
            MovementType.COSTS,
            tx.transaction_number,
            acct_curr,
            exchange_rate,
        )
        tx.add_cash_movement(fee)
        # accrued interest entry for bonds
        if isinstance(product, Product) and product.is_bond():
            ai = product.calculate_accrued_interest(amount, transaction_date)
            if ai:
                ai_mov = CashMovement(
                    tx,
                    -ai * exchange_rate,
                    -ai,
                    MovementType.ACCRUED_INTEREST,
                    tx.transaction_number,
                    acct_curr,
                    exchange_rate,
                )
                tx.add_cash_movement(ai_mov)
        return tx

    def _sell_template(
        self,
        transaction_date,
        portfolio_id,
        account_id,
        portfolio,
        product_collection,
        product_id,
        amount,
        price,
        cost=None,
        exchange_rate=1.0,
        transaction_currency=None,
    ):
        if cost is None:
            cost = self._calculate_cost(amount, price)
        product = product_collection.search_product_id(product_id)
        if product is None:
            raise ValueError("Product not found")
        tx = Transaction(transaction_date, portfolio_id, account_id, portfolio.default_currency)
        sm = SecurityMovement(tx, product_id, amount, price, MovementType.SECURITY_SELL)
        tx.add_security_movement(sm)
        acct_curr = transaction_currency or product.issue_currency
        amt_original = amount * price
        amt_account = amt_original * exchange_rate
        total = CashMovement(
            tx,
            amt_account,
            amt_original,
            MovementType.SECURITY_SELL,
            tx.transaction_number,
            acct_curr,
            exchange_rate,
        )
        tx.add_cash_movement(total)
        fee = CashMovement(
            tx,
            -cost * exchange_rate,
            -cost,
            MovementType.COSTS,
            tx.transaction_number,
            acct_curr,
            exchange_rate,
        )
        tx.add_cash_movement(fee)
        if isinstance(product, Product) and product.is_bond():
            ai = product.calculate_accrued_interest(amount, transaction_date)
            if ai:
                ai_mov = CashMovement(
                    tx,
                    ai * exchange_rate,
                    ai,
                    MovementType.ACCRUED_INTEREST,
                    tx.transaction_number,
                    acct_curr,
                    exchange_rate,
                )
                tx.add_cash_movement(ai_mov)
        return tx

    def _deposit_template(self, transaction_date, portfolio_id, account_id, amount, transaction_currency, **kwargs):
        tx = Transaction(transaction_date, portfolio_id, account_id, transaction_currency)
        cm = CashMovement(tx, amount, amount, MovementType.DEPOSIT, tx.transaction_number, transaction_currency)
        tx.add_cash_movement(cm)
        return tx

    def _dividend_template(self, transaction_date, portfolio_id, account_id, amount, **kwargs):
        tx = Transaction(transaction_date, portfolio_id, account_id, portfolio.default_currency)
        cm = CashMovement(tx, amount, amount, MovementType.INTEREST, tx.transaction_number, portfolio.default_currency)
        tx.add_cash_movement(cm)
        return tx

    def create_transaction(
        self,
        transaction_date,
        portfolio_id,
        template,
        portfolio,
        product_collection=None,
        currency_prices=None,
        **kwargs,
    ) -> Transaction:
        """Build a transaction using a template.

        Parameters mirror the old implementation so that tests written for
        ``OpenPortfolioLib`` continue to work.  ``currency_prices`` is only
        used when the transaction involves a security with a different
        currency than the portfolio's accounts; an exchange rate will be
        obtained automatically.
        """

        if template not in self.templates:
            raise ValueError("Unknown template")

        # Determine account and optional exchange rate
        exchange_rate = kwargs.get("exchange_rate", 1.0)

        if template == TransactionTemplate.DEPOSIT:
            # deposit handles its own currency
            transaction_currency = kwargs.get("transaction_currency")
            account = portfolio.get_account_by_currency(transaction_currency)
            account_id = account.cash_account_id
            acct_curr = account.currency
        else:
            # security transaction, need product
            product_id = kwargs.get("product_id")
            product = product_collection.search_product_id(product_id)
            if product is None:
                raise ValueError(f"Product with ID {product_id} not found")
            transaction_currency = kwargs.get("settlement_currency") or product.issue_currency
            try:
                account = portfolio.get_account_by_currency(transaction_currency)
            except ValueError:
                # use default currency account and compute rate
                account = portfolio.get_account_by_currency(portfolio.default_currency)
                if currency_prices is None:
                    raise ValueError("currency_prices required for cross-currency transactions")
                try:
                    exchange_rate = 1 / currency_prices.get_latest_price(transaction_currency, portfolio.default_currency)
                except ValueError:
                    exchange_rate = currency_prices.get_latest_price(portfolio.default_currency, transaction_currency)
            account_id = account.cash_account_id
            acct_curr = account.currency
        # propagate computed values
        kwargs["exchange_rate"] = exchange_rate
        kwargs["transaction_currency"] = acct_curr
        kwargs.pop("settlement_currency", None)
        # we will forward portfolio and product_collection explicitly below, so
        # remove them from the dynamic kwargs if present to avoid duplication
        kwargs.pop("portfolio", None)
        kwargs.pop("product_collection", None)

        return self.templates[template](
            transaction_date=transaction_date,
            portfolio_id=portfolio_id,
            account_id=account_id,
            portfolio=portfolio,
            product_collection=product_collection,
            **kwargs,
        )

    def execute_transaction(self, tx: Transaction, portfolio: Portfolio, product_collection) -> List[str]:
        # Perform a very simple validation: ensure no cash account would go
        # negative after applying the movements.  The original library had a
        # much more extensive validation routine; for the purposes of the
        # refactor we check only balances.  A richer ``Transaction.validate``
        # may be added later.
        for cm in tx.cash_movements:
            account = portfolio.search_account_id(cm.cash_account_id, currency=cm.transaction_currency)
            if account and account.balance + cm.amount_account_currency < 0:
                raise ValueError(f"Insufficient balance for account {account.cash_account_id}")

        # apply movements
        for sm in tx.security_movements:
            product = product_collection.search_product_id(sm.product_id)
            if product:
                existing = next((h for h in portfolio.securities_account.holdings if h["product"].instrument_id == product.instrument_id), None)
                if existing:
                    existing["amount"] += sm.amount_nominal if sm.movement_type == MovementType.SECURITY_BUY else -sm.amount_nominal
                else:
                    portfolio.securities_account.holdings.append({"product": product, "amount": sm.amount_nominal})
                product.add_transaction(tx)
        for cm in tx.cash_movements:
            acc = portfolio.search_account_id(cm.cash_account_id, currency=cm.transaction_currency)
            if acc:
                acc.balance += cm.amount_account_currency

        for acc in portfolio.cash_accounts.values():
            if tx not in acc.transactions:
                acc.add_transaction(tx)
        self.history.append(tx)
        return [f"Transaction {tx.transaction_number} executed"]

    def create_and_execute_transaction(self, **kwargs) -> List[str]:
        """Convenience: create a transaction and immediately execute it."""
        tx = self.create_transaction(**kwargs)
        return self.execute_transaction(tx, kwargs.get("portfolio"), kwargs.get("product_collection"))
