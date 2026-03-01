from __future__ import annotations
from datetime import date
from typing import Dict, Optional, List, Tuple

# avoid circular import by using TYPE_CHECKING for Transaction
from .enums import AccountType, MovementType
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # pragma: no cover
    from .transactions import Transaction
from .products import Product
from .utils import TimeTravel
import logging


DEFAULT_CURRENCY = "EUR"


class CashAccount:
    def __init__(
        self,
        cash_account_id: int,
        currency: str = DEFAULT_CURRENCY,
        account_type: AccountType = AccountType.CASH,
        start_balance: float = 0.0,
    ):
        self.cash_account_id = cash_account_id
        self.currency = currency
        self.account_type = account_type
        self.start_balance = start_balance
        self.balance = start_balance
        self.transactions: List[Transaction] = []
        self.exchange_rate: float = 1.0

    def get_balance(self, value_date: date) -> float:
        balance = self.start_balance
        for transaction in self.transactions:
            if transaction.transaction_date <= value_date:
                for movement in transaction.cash_movements:
                    balance += movement.amount_account_currency * movement.exchange_rate
        return balance

    def add_transaction(self, transaction: Transaction):
        if transaction not in self.transactions:
            self.transactions.append(transaction)
            logging.info("Added transaction %s to cash account %s", transaction.transaction_number, self.cash_account_id)


class SecuritiesAccount:
    def __init__(self, portfolio_id: int, currency: str = DEFAULT_CURRENCY, start_date: date = date.today()):
        self.portfolio_id = portfolio_id
        self.currency = currency
        self.start_date = start_date
        # each holding is a dict with "product" and "amount"
        self.holdings: List[Dict[str, object]] = []

    def get_holding_values(self, valuation_date: date) -> List[List[object]]:
        results = []
        for holding in self.holdings:
            product: Product = holding["product"]
            amount_on_date = 0
            for transaction in product.transactions:
                for movement in transaction.security_movements:
                    if movement.transaction_date <= valuation_date and movement.product_id == product.instrument_id:
                        if movement.movement_type == MovementType.SECURITY_BUY:
                            amount_on_date += movement.amount_nominal
                        elif movement.movement_type == MovementType.SECURITY_SELL:
                            amount_on_date -= movement.amount_nominal
            if amount_on_date <= 0:
                continue
            price = product.get_price(valuation_date) or 0.0
            value = amount_on_date * price
            if isinstance(product, Bond):
                # time_travel is no longer required by product.calculate_accrued_interest
                accrued_interest = product.calculate_accrued_interest(holding["amount"], valuation_date)
                value += accrued_interest
            results.append([valuation_date, float(value), product.instrument_id, amount_on_date, price, 1])
        return results


class Portfolio:
    def __init__(
        self,
        portfolio_id: int,
        name: str,
        client_id: int,
        default_currency: str = DEFAULT_CURRENCY,
        cost_in_transaction_currency: bool = True,
    ):
        self.portfolio_id = portfolio_id
        self.name = name
        self.client_id = client_id
        self.default_currency = default_currency
        self.cost_in_transaction_currency = cost_in_transaction_currency
        self.cash_accounts: Dict[Tuple[int, str, AccountType], CashAccount] = {}
        self.securities_account = SecuritiesAccount(portfolio_id)
        # automatically create a default cash account
        self.add_cash_account(portfolio_id, currency=default_currency, start_balance=0)

    def __repr__(self):
        return (
            f"Portfolio(Id={self.portfolio_id}, name={self.name}, client={self.client_id}, "
            f"cash_accounts={len(self.cash_accounts)})"
        )

    # account helpers
    def add_cash_account(
        self,
        account_id: int,
        currency: str = DEFAULT_CURRENCY,
        account_type: AccountType = AccountType.CASH,
        start_balance: float = 0.0,
    ) -> CashAccount:
        key = (account_id, currency, account_type)
        if key in self.cash_accounts:
            raise ValueError(f"Account {key} already exists")
        account = CashAccount(account_id, currency, account_type, start_balance)
        self.cash_accounts[key] = account
        logging.info("Added cash account %s to portfolio %s", account_id, self.portfolio_id)
        return account

    def get_account_by_currency(self, currency: str, account_type: AccountType = AccountType.CASH) -> CashAccount:
        for (acc_id, acc_currency, acc_type), account in self.cash_accounts.items():
            if acc_currency == currency and acc_type == account_type:
                return account
        raise ValueError(f"No account found for currency {currency} type {account_type}")

    def search_account_id(
        self, account_id: int, currency: str = DEFAULT_CURRENCY, account_type: AccountType = AccountType.CASH
    ) -> Optional[CashAccount]:
        return self.cash_accounts.get((account_id, currency, account_type))

    # transaction helpers
    def execute_transaction(self, transaction: Transaction, product_collection) -> list[str]:
        return TransactionManager().execute_transaction(transaction, self, product_collection)

    def list_all_transactions(self) -> List[dict]:
        """Return a serializable list of all transactions across cash accounts."""
        seen = set()
        records: List[dict] = []
        for account in self.cash_accounts.values():
            for tx in account.transactions:
                if tx.transaction_number in seen:
                    continue
                seen.add(tx.transaction_number)
                records.append(tx.to_dict())
        return records

    # convenience printing methods copied/rewritten from the previous
    # monolithic implementation.  They are not used by the core logic but
    # remain handy for quick inspection.
    def list_accounts(self) -> None:
        headers = ["Account ID", "Currency", "Account Type", "Balance"]
        rows = []
        for (acct_id, curr, acc_type), acc in self.cash_accounts.items():
            rows.append([acct_id, curr, acc_type.name, acc.balance])
        # securities account as row
        rows.append([self.securities_account.portfolio_id, self.securities_account.currency, "SECURITIES", "N/A"])
        try:
            from tabulate import tabulate
            print(f"Accounts in Portfolio {self.portfolio_id}:")
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        except ImportError:
            for r in rows:
                print(r)

    def list_holdings(self, valuation_date=None, time_travel=None):
        """Display a human-readable table of holdings.

        The old API accepted a ``time_travel`` instance as first argument; for
        backwards compatibility we still allow that positionally.  If
        ``valuation_date`` is ``None`` we use ``time_travel.current_date`` or
        today's date.
        """
        # backward compatibility: allow calling with (time_travel, date)
        from .utils import TimeTravel
        if isinstance(valuation_date, TimeTravel) and time_travel is None:
            time_travel = valuation_date
            valuation_date = None

        if valuation_date is None:
            if time_travel is not None:
                valuation_date = time_travel.current_date
            else:
                valuation_date = date.today()
        if not self.securities_account.holdings:
            print("No holdings in the portfolio.")
            return
        headers = ["Product ID", "Description", "Type", "Amount", "Price", "Value"]
        rows = []
        for holding in self.securities_account.holdings:
            product = holding["product"]
            total_amount = 0
            for tx in product.transactions:
                for mv in tx.security_movements:
                    if mv.transaction_date <= valuation_date and mv.product_id == product.instrument_id:
                        if mv.movement_type == MovementType.SECURITY_BUY:
                            total_amount += mv.amount_nominal
                        elif mv.movement_type == MovementType.SECURITY_SELL:
                            total_amount -= mv.amount_nominal
            if total_amount > 0:
                price = product.get_price(valuation_date) or 0
                rows.append([product.instrument_id, product.description, product.type.name, total_amount, price, total_amount * price])
        try:
            from tabulate import tabulate
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        except ImportError:
            for r in rows:
                print(r)

    def list_transactions(self) -> None:
        headers = ["Trans. Nr", "Date", "Account/Curr", "Type", "Prod ID", "Nom/Amount", "Price", "Value", "FX", "Total", "Acc Type"]
        rows = []
        for tx in self.list_all_transactions():
            for cm in tx["cash_movements"]:
                rows.append([tx["transaction_number"], tx["transaction_date"], f"{tx['portfolio_id']}/{cm['cash_account_id']}/{cm['currency']}", cm['type'], "", "", "", cm['amount'], "", "", AccountType.CASH.value])
            for sm in tx["security_movements"]:
                rows.append([tx["transaction_number"], tx["transaction_date"], f"{tx['portfolio_id']}/{sm['product_id']}", sm['type'], sm['product_id'], sm['amount_nominal'], sm['price'], sm['amount_nominal']*sm['price'], "", "", AccountType.SECURITIES.value])
        try:
            from tabulate import tabulate
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        except ImportError:
            for r in rows:
                print(r)

    # value / returns (copied earlier)
    def calculate_holding_value(self, value_date: date) -> float:
        holdings = self.securities_account.get_holding_values(value_date)
        total = sum(float(v) for _, v, *_ in holdings)
        cash_total = sum(account.get_balance(value_date) * account.exchange_rate for account in self.cash_accounts.values())
        return total + cash_total

    # ... other methods like returns_table, list_holdings, etc. could be included as needed


# For convenience when performing isinstance checks
from .products import Bond
