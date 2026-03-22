from enum import Enum

# Enums used across the package

class TransactionTemplate(Enum):
    BUY = 'purchase'
    SELL = 'sale'
    DIVIDEND = 'dividend'
    DEPOSIT = 'deposit'

class QuotationType(Enum):
    NOMINAL = 'nominal'
    AMOUNT = 'amount'

class TransactionType(Enum):
    CASH = 'cash'
    SECURITY = 'security'

class InterestType(Enum):
    ACT_ACT = 'act/act'
    THIRTY_360 = '30/360'

class PaymentFrequency(Enum):
    MONTH = 'month'
    YEAR = 'year'
    END_DATE = 'end_date'

class AccountType(Enum):
    CASH = 'cash'
    SAVINGS = 'savings'
    OBLIGO = 'obligo'
    DEPOSIT = 'deposit'
    SECURITIES = 'securities'

class InstrumentType(Enum):
    STOCK = 'stock'
    BOND = 'bond'
    FUND = 'fund'
    OPTION = 'option'

class MovementType(Enum):
    TAX = 'tax'
    COSTS = 'costs'
    SECURITY_BUY = 'security_buy'
    SECURITY_SELL = 'security_sell'
    ACCRUED_INTEREST = 'accrued_interest'
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    INTEREST = 'interest'
    CORPORATE_ACTION = 'corporate_action'
    TRANSFER_IN = 'transfer_in'
    TRANSFER_OUT = 'transfer_out'
