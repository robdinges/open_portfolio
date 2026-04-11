"""Domain enumerations used across the portfolio analytics system."""

from enum import Enum


class InstrumentType(str, Enum):
    """Asset class of a financial instrument."""

    STOCK = "STOCK"
    BOND = "BOND"


class TransactionType(str, Enum):
    """Possible transaction types in the ledger."""

    BUY = "BUY"
    SELL = "SELL"
    FEE = "FEE"
    FX = "FX"
    INTEREST = "INTEREST"


class AllocationDimension(str, Enum):
    """Grouping dimension for portfolio allocation breakdowns."""

    ASSET_CLASS = "asset_class"
    CURRENCY = "currency"
    INSTRUMENT = "instrument"
