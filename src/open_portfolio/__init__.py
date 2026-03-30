"""OpenPortfolio package.

Provides a high-level API for portfolio management.
"""

from .enums import *
from .utils import TimeTravel
from .clients import Client
from .accounts import CashAccount, SecuritiesAccount, Portfolio
from .products import Product, Bond, Stock
from .transactions import (
    Transaction,
    CashMovement,
    SecurityMovement,
    TransactionManager,
)
from .prices import CurrencyPrices, ProductPrices
from .product_collection import ProductCollection
from .database import Database
from .order_entry import (
    OrderStatus,
    OrderDraft,
    InMemoryOrderRepository,
    DatabaseOrderRepository,
    ORDER_ENTRY_PLACEHOLDERS,
)
from .web_app import make_app, run as run_web_app
from .sample_data import create_realistic_dataset
from .reporting import PortfolioReporter

__all__ = [
    "TimeTravel",
    "Client",
    "CashAccount",
    "SecuritiesAccount",
    "Portfolio",
    "Product",
    "Bond",
    "Stock",
    "Transaction",
    "CashMovement",
    "SecurityMovement",
    "TransactionManager",
    "CurrencyPrices",
    "ProductPrices",
    "ProductCollection",
    "make_app",
    "run_web_app",
    "Database",
    "OrderStatus",
    "OrderDraft",
    "InMemoryOrderRepository",
    "DatabaseOrderRepository",
    "ORDER_ENTRY_PLACEHOLDERS",
    "create_realistic_dataset",
    "PortfolioReporter",
]
