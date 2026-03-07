from importlib import import_module
from pathlib import Path
import sys

try:
    _portfolio_lib = import_module("OpenPortfolioLib")
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    _portfolio_lib = import_module("OpenPortfolioLib")

_exported = {
    name: value for name, value in vars(_portfolio_lib).items() if not name.startswith("_")
}
globals().update(_exported)

DEFAULT_CURRENCY = _portfolio_lib.DEFAULT_CURRENCY
TransactionTemplate = _portfolio_lib.TransactionTemplate
QuotationType = _portfolio_lib.QuotationType
TransactionType = _portfolio_lib.TransactionType
InterestType = _portfolio_lib.InterestType
PaymentFrequency = _portfolio_lib.PaymentFrequency
AccountType = _portfolio_lib.AccountType
InstrumentType = _portfolio_lib.InstrumentType
MovementType = _portfolio_lib.MovementType
TimeTravel = _portfolio_lib.TimeTravel
Client = _portfolio_lib.Client
ProductCollection = _portfolio_lib.ProductCollection
Portfolio = _portfolio_lib.Portfolio
CashAccount = _portfolio_lib.CashAccount
SecuritiesAccount = _portfolio_lib.SecuritiesAccount
Product = _portfolio_lib.Product
Bond = _portfolio_lib.Bond
Stock = _portfolio_lib.Stock
CashMovement = _portfolio_lib.CashMovement
SecurityMovement = _portfolio_lib.SecurityMovement
TransactionManager = _portfolio_lib.TransactionManager
Transaction = _portfolio_lib.Transaction
CurrencyPrices = _portfolio_lib.CurrencyPrices
ProductPrices = _portfolio_lib.ProductPrices

__all__ = sorted(_exported.keys())
