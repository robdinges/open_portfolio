"""
Abstract repository contracts.

Each repository exposes a small, focused interface for one aggregate root.
Concrete implementations (e.g., SQLite, PostgreSQL, in-memory) conform to
these contracts, making the service layer storage-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from portfolio_analytics.domain.models import (
    CashAccount,
    Client,
    Instrument,
    InstrumentAttributeHistory,
    Portfolio,
    Transaction,
)


class ClientRepository(ABC):
    @abstractmethod
    def save(self, client: Client) -> None: ...

    @abstractmethod
    def get(self, client_id: str) -> Optional[Client]: ...

    @abstractmethod
    def list_all(self) -> list[Client]: ...


class PortfolioRepository(ABC):
    @abstractmethod
    def save(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    def get(self, portfolio_id: str) -> Optional[Portfolio]: ...

    @abstractmethod
    def list_by_client(self, client_id: str) -> list[Portfolio]: ...


class InstrumentRepository(ABC):
    @abstractmethod
    def save(self, instrument: Instrument) -> None: ...

    @abstractmethod
    def get(self, instrument_id: str) -> Optional[Instrument]: ...

    @abstractmethod
    def list_all(self) -> list[Instrument]: ...

    @abstractmethod
    def save_attribute(self, attr: InstrumentAttributeHistory) -> None: ...

    @abstractmethod
    def get_attribute(
        self, instrument_id: str, attribute_name: str, as_of: datetime
    ) -> Optional[str]: ...


class CashAccountRepository(ABC):
    @abstractmethod
    def save(self, account: CashAccount) -> None: ...

    @abstractmethod
    def get(self, account_id: str) -> Optional[CashAccount]: ...

    @abstractmethod
    def list_by_portfolio(self, portfolio_id: str) -> list[CashAccount]: ...

    @abstractmethod
    def find_by_portfolio_and_currency(
        self, portfolio_id: str, currency: str
    ) -> Optional[CashAccount]: ...


class TransactionRepository(ABC):
    @abstractmethod
    def save(self, transaction: Transaction) -> None: ...

    @abstractmethod
    def get(self, transaction_id: str) -> Optional[Transaction]: ...

    @abstractmethod
    def list_by_portfolio(
        self,
        portfolio_id: str,
        up_to: Optional[datetime] = None,
    ) -> list[Transaction]: ...

    @abstractmethod
    def list_by_instrument(
        self,
        instrument_id: str,
        up_to: Optional[datetime] = None,
    ) -> list[Transaction]: ...
