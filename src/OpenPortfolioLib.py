
from datetime import timedelta, date

from typing import Optional
from enum import Enum
import logging
from tabulate import tabulate
DEFAULT_CURRENCY = 'EUR'

# enum classes

class TransactionTemplate(Enum):
    BUY = 'purchase'
    SELL = 'sale'
    DIVIDEND = 'dividend'

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

# helper class

class TimeTravel:
    def __init__(self):
        self.current_date = date.today()

    def skip_days(self, days_to_skip=1):
        if days_to_skip <= 0:
            raise ValueError("Number of days to skip must be a positive integer.")
        self.current_date += timedelta(days=days_to_skip)
        logging.info("Skipped %s days. New date: %s", days_to_skip, self.current_date)
        return self.current_date

    def is_weekend(self, day):
        return day.weekday() >= 5

    def skip_working_days(self, working_days_to_skip=1):
        if working_days_to_skip <= 0:
            raise ValueError("Number of working days to skip must be a positive integer.")
        days_skipped = 0
        while days_skipped < working_days_to_skip:
            self.current_date += timedelta(days=1)
            if not self.is_weekend(self.current_date):
                days_skipped += 1
        logging.info("Skipped {working_days_to_skip} working days. New date: {self.current_date}")
        return self.current_date

    def go_to_date(self, new_date: date):
        """
        tbd
        """
        if new_date <= self.current_date:
            raise ValueError("New date must be after the current date.")
        if self.is_weekend(new_date):
            raise ValueError("New date must not be a weekend.")
        self.current_date = new_date
        logging.info("Moved to new date: %s", self.current_date)
        return self.current_date

# client and portfolio classes

class Client:
    def __init__(self, client_id, name):
        self.client_id = client_id
        self.name = name
        self.portfolios = []

    def add_portfolio(self, portfolio_id, default_currency='EUR', cost_in_transaction_currency=True):
        for portfolio in self.portfolios:
            if portfolio.portfolio_id == portfolio_id:
                raise ValueError(f"Portfolio with ID {portfolio_id} already exists for client {self.client_id}.")
        portfolio = Portfolio(portfolio_id, self.name, self.client_id, default_currency, cost_in_transaction_currency)
        self.portfolios.append(portfolio)
        logging.info("Added portfolio %s to client %s", portfolio_id, self.client_id)
        return portfolio

class ProductCollection:
    def __init__(self):
        self.products = {}

    def add_product(self, product):
        self.products[product.instrument_id] = product

    def search_product_id(self, product_id):
        return self.products.get(product_id)

    def list_products(self):
        if not self.products:
            print("No products in the collection.")
            return
        print("Product Collection:")
        headers = [
            "Instrument ID", "Description", "Type", 
            "Minimum Purchase Value", "Smallest Trading Unit", 
            "Issue Currency", "Start Date", "Maturity Date", 
            "Interest Rate", "Payment Frequency"
        ]
        table_data = []
        for product in self.products.values():
            if isinstance(product, Bond):
                row = [
                    product.instrument_id,
                    product.description,
                    product.type.name,
                    product.minimum_purchase_value,
                    product.smallest_trading_unit,
                    product.issue_currency,
                    product.start_date,
                    product.maturity_date,
                    product.interest_rate,
                    product.interest_payment_frequency.name
                ]
            else:
                row = [
                    product.instrument_id,
                    product.description,
                    product.type.name,
                    product.minimum_purchase_value,
                    product.smallest_trading_unit,
                    product.issue_currency,
                    "N/A",  # Start Date
                    "N/A",  # Maturity Date
                    "N/A",  # Interest Rate
                    "N/A"   # Payment Frequency
                ]
            table_data.append(row)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))
# account classes

class CashAccount:
    def __init__(self, cash_account_id, currency='EUR', account_type=AccountType.CASH, start_balance=0):
        self.cash_account_id = cash_account_id
        self.currency = currency
        self.account_type = account_type
        self.start_balance = start_balance
        self.balance = start_balance
        self.transactions = []
        self.exchange_rate = 1.0

    def get_balance(self, value_date):
        balance = self.start_balance
        for transaction in self.transactions:
            if transaction.transaction_date <= value_date:
                for movement in transaction.cash_movements:
                    balance += movement.amount_account_currency * movement.exchange_rate
        return balance

    def add_transaction(self, transaction):
        if transaction not in self.transactions:
            self.transactions.append(transaction)
            logging.info("Added transaction %s to cash account %s", transaction.transaction_number, self.cash_account_id)

class SecuritiesAccount:

    def __init__(self, portfolio_id: int, currency: str = DEFAULT_CURRENCY, start_date: date = date.today()):
        self.portfolio_id = portfolio_id
        self.currency = currency
        self.start_date = start_date
        self.holdings = []

    def get_holding_values(self, valuation_date):
        holding_values = []

        for holding in self.holdings:
            product = holding['product']
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

            price = product.get_price(valuation_date)
            currency_price = 1

            if price is None or price == "N/A":
                price = 0.0

            value = amount_on_date * price * currency_price

            if isinstance(product, Bond):
                time_travel = TimeTravel()
                accrued_interest = product.calculate_accrued_interest(holding['amount'], time_travel, valuation_date)
                value += accrued_interest

            holding_values.append([valuation_date, float(value), product.instrument_id, amount_on_date, price, currency_price])

        return holding_values

class Portfolio:
    def __init__(self, portfolio_id, name, client_id, default_currency='EUR', cost_in_transaction_currency=True):
        self.portfolio_id = portfolio_id
        self.name = name
        self.client_id = client_id
        self.default_currency = default_currency
        self.cost_in_transaction_currency = cost_in_transaction_currency
        self.cash_accounts = {}
        self.securities_account = SecuritiesAccount(portfolio_id)
        self.add_cash_account(self.portfolio_id, currency=self.default_currency, start_balance=0)

    def __repr__(self):
        return (f'Portfolio Id: {self.portfolio_id}, Name: {self.name}, Client Id: {self.client_id}, '
                f'Nr of cash accounts: {len(self.cash_accounts)}')

    def add_cash_account(self, account_id: int, currency='EUR', account_type=AccountType.CASH, start_balance=0):
        account_key = (account_id, currency, account_type)
        if account_key in self.cash_accounts:
            raise ValueError(f"Account with ID {account_id}, currency {currency}, and type {account_type} already exists.")
        cash_account = CashAccount(
            account_id,
            currency,
            account_type=account_type,
            start_balance=start_balance
        )
        self.cash_accounts[account_key] = cash_account
        logging.info("Added cash account %s to portfolio %s", account_id, self.portfolio_id)

    def search_account_id(self, account_id: int, currency='EUR', account_type=AccountType.CASH) -> int:
        account_key = (account_id, currency, account_type)
        return self.cash_accounts.get(account_key)

    def get_account_by_currency(self, currency, account_type=AccountType.CASH) -> CashAccount:
        for (account_id, acc_currency, acc_type), account in self.cash_accounts.items():
            if acc_currency == currency and acc_type == account_type:
                return account
        
        # If not found, raise an error
        raise ValueError(f"No account found for currency {currency} and type {account_type} in portfolio {self.portfolio_id}")

    def search_account_id_by_currency(self, currency, account_type=AccountType.CASH) -> Optional[CashAccount]:
        for (account_id, acc_currency, acc_type), account in self.cash_accounts.items():
            if acc_currency == currency and acc_type == account_type:
                return account
        return None

    def execute_transaction(self, transaction, product_collection):
        transaction.convert_cash_account_ids_to_int()  # Ensure cash_account_id is an integer before execution

        is_valid, messages = transaction.validate_transaction(self, product_collection)
        if not is_valid:
            for message in messages:
                logging.error(message)
            return messages

        # Process security movements
        for movement in transaction.security_movements:
            product = product_collection.search_product_id(movement.product_id)
            if product:
                existing_holding = next((h for h in self.securities_account.holdings if h['product'].instrument_id == product.instrument_id), None)
                if existing_holding:
                    existing_holding['amount'] += movement.amount_nominal
                else:
                    self.securities_account.holdings.append({
                        'product': product,
                        'amount': movement.amount_nominal
                    })
                product.add_transaction(transaction)

        # Process cash movements
        for movement in transaction.cash_movements:
            account = self.search_account_id(movement.cash_account_id, currency=movement.transaction_currency, account_type=AccountType.CASH)
            if account:
                logging.info("Before updating balance: %s", account.balance)
                account.balance += movement.amount_account_currency
                logging.info("After updating balance: %s", account.balance)
            else:
                raise ValueError(f"Cash account {movement.cash_account_id} not found.")

        for account in self.cash_accounts.values():
            if transaction not in account.transactions:
                account.add_transaction(transaction)

        logging.info("Transaction executed: %s", transaction.transaction_number)
        return [f"Transaction {transaction.transaction_number} successfully executed."]

    def calculate_return(self, start_date, end_date):
        capital_change_types = {MovementType.DEPOSIT, MovementType.WITHDRAWAL,
                                MovementType.TRANSFER_IN, MovementType.TRANSFER_OUT}

        capital_changes = []

        for account in self.cash_accounts.values():
            for transaction in account.transactions:
                for movement in transaction.cash_movements:
                    if movement.movement_type in capital_change_types and start_date <= movement.transaction_date <= end_date:
                        capital_changes.append(movement.transaction_date)

        for holding in self.securities_account.holdings:
            for transaction in holding['product'].transactions:
                for movement in transaction.security_movements:
                    if movement.movement_type in capital_change_types and start_date <= movement.transaction_date <= end_date:
                        capital_changes.append(movement.transaction_date)

        capital_changes.sort()

        periods = []
        current_start_date = start_date
        for change_date in capital_changes:
            if current_start_date < change_date:
                periods.append((current_start_date, change_date - timedelta(days=1)))
            current_start_date = change_date

        if current_start_date <= end_date:
            periods.append((current_start_date, end_date))

        periodic_returns = []
        cumulative_return_amount = 0
        cumulative_return_percentage = 1

        for start_of_period, end_of_period in periods:
            if start_of_period <= end_of_period:
                a = self.calculate_holding_value(start_of_period)
                b = self.calculate_holding_value(end_of_period)
                return_amount = b - a
                cumulative_return_amount += return_amount
                return_percentage = (return_amount / a) if a != 0 else 0
                cumulative_return_percentage *= (1 + return_percentage)
                periodic_returns.append([
                    start_of_period, end_of_period, b, a, return_amount,
                    return_percentage, cumulative_return_amount,
                    cumulative_return_percentage - 1
                ])

        return periodic_returns

    def calculate_holding_value(self, value_date):
        holding_values = self.securities_account.get_holding_values(value_date)
        total_value_on_value_date = sum(float(value) for _, value, *_ in holding_values)
        total_cash_value = sum(
            float(account.get_balance(value_date) * account.exchange_rate)  # Houd rekening met de valutakoers
            for account in self.cash_accounts.values()
        )
        total_value_on_value_date += total_cash_value

        logging.info("Calculated total portfolio value for date %s: %s", value_date, total_value_on_value_date)

        return total_value_on_value_date

    def returns_table(self, start_date, end_date):
        """
        tbd
        """
        returns = self.calculate_return(start_date, end_date)

        headers = ["Start Date", "End Date", "End Value", "Start Value", "Return Amount", "Return Percentage", "Cumulative Return Amount", "Cumulative Return Percentage"]

        table_data = []
        for period in returns:
            row = [
                period[0],
                period[1],
                period[2],
                period[3],
                period[4],
                f"{period[5]*100:.2f}%",
                period[6],
                f"{period[7]*100:.2f}%"
            ]
            table_data.append(row)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def list_all_transactions(self):
        transactions = []

        def find_transaction_data(transaction_number):
            for t in transactions:
                if t['transaction_number'] == transaction_number:
                    return t
            return None

        for account in self.cash_accounts.values():
            for transaction in account.transactions:
                transaction_data = find_transaction_data(transaction.transaction_number)
                if transaction_data is None:
                    transaction_data = {
                        'transaction_number': transaction.transaction_number,
                        'date': transaction.transaction_date,
                        'cash_movements': [],
                        'security_movements': [],
                        'account_id': account.cash_account_id,
                        'portfolio_id': self.portfolio_id,
                        'account_type': account.account_type.name,
                    }
                    transactions.append(transaction_data)

                for cash_movement in transaction.cash_movements:
                    if not any(cm['amount'] == cash_movement.amount_account_currency and cm['movement_type'] == cash_movement.movement_type for cm in transaction_data['cash_movements']):
                        logging.info("Adding cash movement: %s, %s", cash_movement.amount_account_currency, cash_movement.movement_type)
                        transaction_data['cash_movements'].append({
                            'movement_type': cash_movement.movement_type,
                            'amount': cash_movement.amount_account_currency,
                            'original_amount': cash_movement.amount_original_currency,
                        })

        for holding in self.securities_account.holdings:
            for transaction in holding['product'].transactions:
                transaction_data = find_transaction_data(transaction.transaction_number)
                if transaction_data is None:
                    transaction_data = {
                        'transaction_number': transaction.transaction_number,
                        'date': transaction.transaction_date,
                        'cash_movements': [],
                        'security_movements': [],
                        'account_id': 'securities',
                        'portfolio_id': self.portfolio_id,
                        'account_type': 'SECURITIES',
                    }
                    transactions.append(transaction_data)

                for security_movement in transaction.security_movements:
                    if not any(sm['amount_nominal'] == security_movement.amount_nominal and sm['product_id'] == security_movement.product_id for sm in transaction_data['security_movements']):
                        logging.info("Adding security movement: %s, %s", security_movement.amount_nominal, security_movement.product_id)
                        transaction_data['security_movements'].append({
                            'movement_type': security_movement.movement_type,
                            'amount_nominal': security_movement.amount_nominal,
                            'price': security_movement.price,
                            'product_id': security_movement.product_id,
                        })

        transactions.sort(key=lambda x: x['date'])
        return transactions

    def transactions_table(self):
        """
        tbd
        """
        transactions = self.list_all_transactions()

        headers = ["Transaction Number", "Date", "Movement Type", "Amount", "Original Amount", "Account ID", "Portfolio ID", "Amount Nominal", "Price", "Product ID", "Account Type"]

        table_data = []
        for tx in transactions:
            # Fetch and display cash movements
            for cm in tx['cash_movements']:
                account = self.search_account_id(tx['account_id'])
                account_type = account.account_type.name if account else "UNKNOWN"
                row = [
                    tx.get('transaction_number', ''),
                    tx.get('date', ''),
                    cm.get('movement_type', ''),
                    cm.get('amount', ''),
                    cm.get('original_amount', ''),
                    tx.get('account_id', ''),
                    tx.get('portfolio_id', ''),
                    '',  # No nominal amount for cash movements
                    '',  # No price for cash movements
                    '',  # No product ID for cash movements
                    account_type
                ]
                table_data.append(row)

            # Fetch and display security movements
            for sm in tx['security_movements']:
                account_type = "SECURITIES"
                row = [
                    tx.get('transaction_number', ''),
                    tx.get('date', ''),
                    sm.get('movement_type', ''),
                    '',  # No cash amount for security movements
                    '',  # No original amount for security movements
                    tx.get('account_id', ''),
                    tx.get('portfolio_id', ''),
                    sm.get('amount_nominal', ''),
                    sm.get('price', ''),
                    sm.get('product_id', ''),
                    account_type
                ]
                table_data.append(row)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def list_holdings(self, time_travel, valuation_date=None):
        """
        Lists the holdings in the portfolio for the given valuation date.
        If no valuation date is provided, uses the current date from TimeTravel.

        Args:
            time_travel (TimeTravel): The TimeTravel instance to get the current date if valuation_date is not provided.
            valuation_date (date, optional): The date to evaluate the holdings. Defaults to None.
        """
        if valuation_date is None:
            valuation_date = time_travel.current_date

        if not self.securities_account.holdings:
            print("No holdings in the portfolio.")
            return

        print(f"Holdings in Portfolio as of {valuation_date}:")
        headers = ["Product ID", "Description", "Type", "Amount", "Price", "Value"]
        table_data = []

        for holding in self.securities_account.holdings:
            product = holding['product']
            total_amount = 0
            for transaction in product.transactions:
                for movement in transaction.security_movements:
                    if movement.transaction_date <= valuation_date and movement.product_id == product.instrument_id:
                        if movement.movement_type == MovementType.SECURITY_BUY:
                            total_amount += movement.amount_nominal
                        elif movement.movement_type == MovementType.SECURITY_SELL:
                            total_amount -= movement.amount_nominal

            if total_amount > 0:
                price = product.get_price(valuation_date)
                value = total_amount * price
                table_data.append([
                    product.instrument_id,
                    product.description,
                    product.type.name,
                    total_amount,
                    price,
                    value
                ])

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def list_accounts(self):
        headers = ["Account ID", "Currency", "Account Type", "Balance"]
        table_data = []
        for (account_id, currency, account_type), account in self.cash_accounts.items():
            table_data.append([account_id, currency, account_type.name, account.balance])
        
        # Add the securities account as well
        securities_account_row = [
            self.securities_account.portfolio_id, 
            self.securities_account.currency, 
            "Securities", 
            "N/A"  # Securities accounts do not have a balance like cash accounts
        ]
        table_data.append(securities_account_row)

        print(f"Accounts in Portfolio {self.portfolio_id}:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def print_account_balance(self, account_id: int, currency='EUR', account_type=AccountType.CASH):
        """
        Print the balance of a given account.

        Args:
            account_id (int): The ID of the account.
            currency (str): The currency of the account. Defaults to 'EUR'.
            account_type (AccountType): The type of the account. Defaults to AccountType.CASH.
        """
        account = self.search_account_id(account_id, currency, account_type)
        if account:
            print(f"Balance for account {account_id}: {account.balance}")

class PortfolioAnalytics:
    def __init__(self, portfolio):
        """
        Initialize the PortfolioAnalytics class.

        Args:
            portfolio (Portfolio): The portfolio to analyze.
        """
        self.portfolio = portfolio

    def get_holdings_progress(self, product_id):
        """
        Get the progress of holdings for a specific product over time.
        
        Args:
            product_id (int): The ID of the product to track.
        
        Returns:
            list: A list of dictionaries containing the date, amount, price, and value of the holdings.
        """
        holdings_progress = []
        changes = set()

        # Find the product in the portfolio's holdings
        for holding in self.portfolio.securities_account.holdings:
            if holding['product'].instrument_id == product_id:
                product = holding['product']
                amount_on_date = 0

                # Collect changes in amount and price
                for transaction in product.transactions:
                    for movement in transaction.security_movements:
                        if movement.product_id == product_id:
                            changes.add(movement.transaction_date)
                            if movement.movement_type == MovementType.SECURITY_BUY:
                                amount_on_date += movement.amount_nominal
                            elif movement.movement_type == MovementType.SECURITY_SELL:
                                amount_on_date -= movement.amount_nominal

                # Add price changes
                for price_date, _ in product.prices:
                    changes.add(price_date)

        # Sort changes by date
        changes = sorted(changes)

        # Track holdings progress over time
        amount_on_date = 0
        for change_date in changes:
            price = product.get_price(change_date)
            for transaction in product.transactions:
                for movement in transaction.security_movements:
                    if movement.transaction_date == change_date and movement.product_id == product_id:
                        if movement.movement_type == MovementType.SECURITY_BUY:
                            amount_on_date += movement.amount_nominal
                        elif movement.movement_type == MovementType.SECURITY_SELL:
                            amount_on_date -= movement.amount_nominal

            value = amount_on_date * price if price != "N/A" else 0
            holdings_progress.append({
                "Date": change_date,
                "Amount": amount_on_date,
                "Price": price,
                "Value": value
            })

        return holdings_progress

# product classes

class Product:
    def __init__(self, instrument_id, description, product_type, minimum_purchase_value, smallest_trading_unit, issue_currency):
        self.instrument_id = instrument_id
        self.description = description
        self.type = product_type
        self.minimum_purchase_value = minimum_purchase_value
        self.smallest_trading_unit = smallest_trading_unit
        self.issue_currency = issue_currency
        self.prices = []
        self.transactions = []

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
        logging.info("Added transaction to product %s", self.instrument_id)

    def is_bond(self):
        return self.type == InstrumentType.BOND

    def add_price(self, date, price):
        self.prices.append((date, price))
        self.prices.sort()
        logging.info("Added price for product %1 on %1",self.instrument_id, date)

    def get_price(self, date):
        last_price = None
        for price_date, price in self.prices:
            if price_date <= date:
                last_price = price
            else:
                break
        return last_price if last_price is not None else "N/A"

    def get_details(self):
        return {
            "ID": self.instrument_id,
            "Description": self.description,
            "Type": self.type,
            "Minimum Purchase Value": self.minimum_purchase_value,
            "Smallest Trading Unit": self.smallest_trading_unit,
            "Issue Currency": self.issue_currency
        }

class Bond(Product):
    def __init__(
            self, 
            instrument_id, 
            description, 
            minimum_purchase_value, 
            smallest_trading_unit, 
            issue_currency, 
            start_date, 
            maturity_date, 
            interest_rate, 
            interest_payment_frequency
            ):
        super().__init__(
            instrument_id, 
            description, 
            InstrumentType.BOND, 
            minimum_purchase_value, 
            smallest_trading_unit, 
            issue_currency
            )
        self.start_date = start_date
        self.maturity_date = maturity_date
        self.interest_rate = interest_rate
        self.interest_payment_frequency = interest_payment_frequency

    def calculate_accrued_interest(self, nominal_value, time_travel, valuation_date, interest_type=InterestType.ACT_ACT):
        """Calculate accrued interest for the bond up to the valuation date."""
        if interest_type == InterestType.ACT_ACT:
            return self.calculate_accrued_interest_act_act(nominal_value, valuation_date)
        elif interest_type == InterestType.THIRTY_360:
            return self.calculate_accrued_interest_thirty_360(nominal_value, valuation_date)
        else:
            raise ValueError("Unsupported interest type")

    def calculate_accrued_interest_act_act(self, nominal_value, valuation_date):
        """Calculate accrued interest using ACT/ACT convention."""
        days_in_year = 366 if self.is_leap_year_in_period(self.start_date, valuation_date) else 365
        days_accrued = (valuation_date - self.start_date).days
        accrued_interest = nominal_value * self.interest_rate * (days_accrued / days_in_year)
        return accrued_interest

    def is_leap_year_in_period(self, start_date, end_date):
        """Check if there is a leap year in the period."""
        current_date = start_date
        while current_date <= end_date:
            if current_date.month == 2 and current_date.day == 29:
                return True
            current_date += timedelta(days=1)
        return False

    def calculate_accrued_interest_thirty_360(self, nominal_value, valuation_date):
        """Dummy implementation for 30/360 convention."""
        days_in_year = 360
        days_accrued = ((valuation_date.year - self.start_date.year) * 360 +
                        (valuation_date.month - self.start_date.month) * 30 +
                        (valuation_date.day - self.start_date.day))
        accrued_interest = nominal_value * self.interest_rate * (days_accrued / days_in_year)
        return accrued_interest

class Stock(Product):
    def __init__(self, product_id, description, minimum_purchase_value, smallest_trading_unit, issue_currency):
        super().__init__(product_id, description, InstrumentType.STOCK, minimum_purchase_value, smallest_trading_unit, issue_currency)

# transaction classes

class CashMovement:

    def __init__(self, transaction, amount_account_currency, amount_original_currency, movement_type: MovementType, transaction_number, transaction_currency, exchange_rate=1.0):
        #self.cash_account_id = transaction.account_id  # Zorg ervoor dat dit een integer ID is
        if isinstance(transaction.account_id, CashAccount):
            self.cash_account_id = transaction.account_id.cash_account_id
        else:
            self.cash_account_id = transaction.account_id
        self.portfolio_id = transaction.portfolio_id
        self.transaction_date = transaction.transaction_date
        self.amount_account_currency = amount_account_currency
        self.amount_original_currency = amount_original_currency
        self.movement_type = movement_type
        self.transaction_number = transaction_number
        self.exchange_rate = exchange_rate
        self.transaction_currency = transaction_currency

class SecurityMovement:
    def __init__(self, transaction, product_id, amount_nominal, price, movement_type: MovementType):
        self.movement_type = movement_type
        self.product_id = product_id
        self.account_id = transaction.account_id
        self.portfolio_id = transaction.portfolio_id
        self.amount_nominal = amount_nominal
        self.price = price
        self.date = transaction.transaction_date
        self.transaction_number = transaction.transaction_number
        self.transaction_date = transaction.transaction_date  # Add this line to include the transaction_date

class TransactionManager:

    def __init__(self):
        self.transaction_history = []
        self.templates = {
            TransactionTemplate.BUY: self.buy_template,
            TransactionTemplate.SELL: self.sell_template,
            TransactionTemplate.DIVIDEND: self.dividend_template
        }

    @staticmethod
    def calculate_cost(transaction_type, amount, price):
        # Placeholder for cost calculation logic
        # For example, let's assume a flat fee of 1% of the transaction value
        return 0.01 * amount * price

    def buy_template(self, transaction_date, portfolio_id, account_id, portfolio, product_collection, product_id, amount, price, cost=None, exchange_rate=1.0):
        if cost is None:
            cost = self.calculate_cost(TransactionTemplate.BUY, amount, price)

        product = product_collection.search_product_id(product_id)
        if product is None:
            logging.error("Product with ID %s not found", product_id)
            return None

        transaction = Transaction(transaction_date, portfolio_id, account_id, portfolio.default_currency)
        security_movement = SecurityMovement(
            transaction=transaction,
            product_id=product_id,
            amount_nominal=amount,
            price=price,
            movement_type=MovementType.SECURITY_BUY
        )
        transaction.add_security_movement(security_movement)

        # Zorg ervoor dat cash_account_id correct is ingesteld
        if isinstance(account_id, CashAccount):
            cash_account_id = account_id.cash_account_id
        else:
            cash_account_id = account_id

        total_movement = CashMovement(
            transaction=transaction,
            amount_account_currency=-amount * price,
            amount_original_currency=-amount * price * exchange_rate,
            movement_type=MovementType.SECURITY_BUY,
            transaction_number=transaction.transaction_number,
            transaction_currency=product.issue_currency,  # Set correct currency
            exchange_rate=exchange_rate
        )
        total_movement.cash_account_id = cash_account_id  # Ensure this is an integer ID
        transaction.add_cash_movement(total_movement)

        cost_movement = CashMovement(
            transaction=transaction,
            amount_account_currency=-cost,
            amount_original_currency=-cost * exchange_rate,
            movement_type=MovementType.COSTS,
            transaction_number=transaction.transaction_number,
            transaction_currency=product.issue_currency,  # Set correct currency
            exchange_rate=exchange_rate
        )
        cost_movement.cash_account_id = cash_account_id  # Ensure this is an integer ID
        transaction.add_cash_movement(cost_movement)

        if isinstance(product, Bond):
            time_travel = TimeTravel()
            accrued_interest = product.calculate_accrued_interest(amount, time_travel, transaction_date)

            ai_movement = CashMovement(
                transaction=transaction,
                amount_account_currency=-accrued_interest,
                amount_original_currency=-accrued_interest * exchange_rate,
                movement_type=MovementType.ACCRUED_INTEREST,
                transaction_number=transaction.transaction_number,
                transaction_currency=product.issue_currency,  # Set correct currency
                exchange_rate=exchange_rate
            )
            ai_movement.cash_account_id = cash_account_id  # Ensure this is an integer ID
            transaction.add_cash_movement(ai_movement)

        logging.info("Created buy transaction %s for portfolio %s", transaction.transaction_number, portfolio_id)
        return transaction

    def sell_template(self, transaction_date, portfolio_id, account_id: int, portfolio, product_collection, product_id, amount, price, cost=None, exchange_rate=1.0):
        if cost is None:
            cost = self.calculate_cost(TransactionTemplate.SELL, amount, price)

        # Retrieve the product from the collection
        product = product_collection.search_product_id(product_id)
        if product is None:
            logging.error("Product with ID %s not found", product_id)
            return None

        transaction = Transaction(transaction_date, portfolio_id, account_id, portfolio.default_currency)
        security_movement = SecurityMovement(
            transaction=transaction,
            product_id=product_id,
            amount_nominal=amount,
            price=price,
            movement_type=MovementType.SECURITY_SELL
        )
        transaction.add_security_movement(security_movement)

        total_movement = CashMovement(
            transaction=transaction,
            amount_account_currency=amount * price,
            amount_original_currency=amount * price * exchange_rate,
            movement_type=MovementType.SECURITY_SELL,
            transaction_number=transaction.transaction_number,
            transaction_currency=product.issue_currency,  # Set correct currency
            exchange_rate=exchange_rate
        )
        transaction.add_cash_movement(total_movement)

        cost_movement = CashMovement(
            transaction=transaction,
            amount_account_currency=-cost,
            amount_original_currency=-cost * exchange_rate,
            movement_type=MovementType.COSTS,
            transaction_number=transaction.transaction_number,
            transaction_currency=product.issue_currency,  # Set correct currency
            exchange_rate=exchange_rate
        )
        transaction.add_cash_movement(cost_movement)

        if isinstance(product, Bond):
            time_travel = TimeTravel()
            accrued_interest = product.calculate_accrued_interest(amount, time_travel, transaction_date)

            ai_movement = CashMovement(
                transaction=transaction,
                amount_account_currency=accrued_interest,
                amount_original_currency=accrued_interest * exchange_rate,
                movement_type=MovementType.ACCRUED_INTEREST,
                transaction_number=transaction.transaction_number,
                transaction_currency=product.issue_currency,  # Set correct currency
                exchange_rate=exchange_rate
            )
            transaction.add_cash_movement(ai_movement)

        logging.info("Created sell transaction %s for portfolio %s", transaction.transaction_number, portfolio_id)
        return transaction

    def dividend_template(self, transaction_date, portfolio_id, account_id, amount):
        transaction = Transaction(transaction_date, portfolio_id, account_id)
        cash_movement = CashMovement(
            transaction=transaction,
            amount_account_currency=amount,
            amount_original_currency=amount,
            movement_type=MovementType.INTEREST,
            transaction_number=transaction.transaction_number
        )
        transaction.add_cash_movement(cash_movement)
        return transaction

    def execute_transaction(self, transaction, portfolio, product_collection):
        logging.debug("Executing transaction...")
        is_valid, messages = transaction.validate_transaction(portfolio, product_collection)
        if not is_valid:
            logging.error(f"Transaction validation failed with messages: {messages}")
            return messages

        for movement in transaction.security_movements:
            product = product_collection.search_product_id(movement.product_id)
            if product:
                existing_holding = next((h for h in portfolio.securities_account.holdings if h['product'].instrument_id == product.instrument_id), None)
                if existing_holding:
                    existing_holding['amount'] += movement.amount_nominal
                else:
                    portfolio.securities_account.holdings.append({
                        'product': product,
                        'amount': movement.amount_nominal
                    })
                product.add_transaction(transaction)
            logging.debug(f"Processed security movement for product {movement.product_id}")

        for movement in transaction.cash_movements:
            account = None
            if movement.cash_account_id == transaction.account_id:
                try:
                    account = portfolio.search_account_id(transaction.account_id)
                except ValueError:
                    account = portfolio.search_account_id(portfolio.default_currency)
            if account:
                account.balance += movement.amount_account_currency
                logging.debug(f"Updated balance for account {account.cash_account_id}: {account.balance}")
            else:
                logging.error(f"Cash account {movement.cash_account_id} not found in portfolio {portfolio.portfolio_id}.")
                raise ValueError(f"Cash account {movement.cash_account_id} not found in portfolio {portfolio.portfolio_id}.")

        for account in portfolio.cash_accounts.values():
            if transaction not in account.transactions:
                account.add_transaction(transaction)

        logging.info("Transaction executed: %s", transaction.transaction_number)
        return [f"Transaction {transaction.transaction_number} successfully executed."]

    def record_transaction(self, transaction):
        self.transaction_history.append(transaction)
        logging.info("Transaction recorded: %s", transaction.transaction_number)

    def generate_report(self, transaction, portfolio, product_collection):
        return transaction.generate_report(portfolio, product_collection)

    def create_transaction(self, transaction_date, portfolio_id, template, portfolio, product_collection, currency_prices, **kwargs):
        logging.debug("Creating transaction...")
        
        if template not in self.templates:
            raise ValueError(f"Unknown template: {template}")

        product_id = kwargs.get('product_id')
        product = product_collection.search_product_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        transaction_currency = product.issue_currency
        logging.debug(f"Transaction currency: {transaction_currency}")

        try:
            account = portfolio.get_account_by_currency(transaction_currency)
            exchange_rate = 1.0
            logging.debug(f"Found account in transaction currency: {account.cash_account_id}")
        except ValueError:
            account = portfolio.get_account_by_currency(portfolio.default_currency)
            logging.debug(f"Using default currency account: {account.cash_account_id}")
            try:
                exchange_rate = 1 / currency_prices.get_latest_price(transaction_currency, portfolio.default_currency)
            except ValueError:
                exchange_rate = currency_prices.get_latest_price(portfolio.default_currency, transaction_currency)
            logging.debug(f"Exchange rate: {exchange_rate}")

        account_id = account.cash_account_id
        kwargs['exchange_rate'] = exchange_rate

        transaction = self.templates[template](transaction_date, portfolio_id, account_id, portfolio, product_collection, **kwargs)
        
        # Ensure the transaction is unique for each portfolio
        transaction.portfolio_id = portfolio_id
        transaction.account_id = account_id
        logging.debug(f"Created transaction {transaction.transaction_number} with account_id {account_id}")

        return transaction

    def create_and_execute_transaction(self, transaction_date, portfolio_id, template, portfolio, product_collection, currency_prices, **kwargs):
        transaction = self.create_transaction(transaction_date, portfolio_id, template, portfolio, product_collection, currency_prices, **kwargs)
        return self.execute_transaction(transaction, portfolio, product_collection)

class Transaction:
    transaction_counter = 0
    def __init__(self, transaction_date, portfolio_id, account_id: int, transaction_currency):
        Transaction.transaction_counter += 1
        self.transaction_number = Transaction.transaction_counter
        self.transaction_date = transaction_date
        self.portfolio_id = portfolio_id
        self.account_id = account_id
        self.transaction_currency = transaction_currency
        self.cash_movements = []
        self.security_movements = []
        logging.info("Transaction %s created on %s", self.transaction_number, self.transaction_date)

    def convert_cash_account_ids_to_int(self):
        for movement in self.cash_movements:
            if isinstance(movement.cash_account_id, CashAccount):
                movement.cash_account_id = movement.cash_account_id.cash_account_id

    def execute(self, portfolio, product_collection):
        self.convert_cash_account_ids_to_int()  # Ensure cash_account_id is an integer before execution

        is_valid, messages = self.validate_transaction(portfolio, product_collection)
        if not is_valid:
            for message in messages:
                logging.error(message)
            return messages

        for movement in self.security_movements:
            product = product_collection.search_product_id(movement.product_id)
            if product:
                existing_holding = next((h for h in portfolio.securities_account.holdings if h['product'].instrument_id == product.instrument_id), None)
                if existing_holding:
                    existing_holding['amount'] += movement.amount_nominal
                else:
                    portfolio.securities_account.holdings.append({
                        'product': product,
                        'amount': movement.amount_nominal
                    })
                product.add_transaction(self)

        for movement in self.cash_movements:
            account = portfolio.search_account_id(movement.cash_account_id, currency=movement.transaction_currency, account_type=AccountType.CASH)
            if account:
                account.balance += movement.amount_account_currency

        account = portfolio.search_account_id(self.account_id, currency=self.transaction_currency, account_type=AccountType.CASH)
        if account and self not in account.transactions:
            account.add_transaction(self)

        logging.info("Transaction executed: %s", self.transaction_number)
        return [f"Transaction {self.transaction_number} successfully executed."]

    def add_cash_movement(self, cash_movement):
        if cash_movement not in self.cash_movements:
            self.cash_movements.append(cash_movement)
            logging.info("Added cash movement to transaction %s: %s at exchange rate %s", self.transaction_number, cash_movement, cash_movement.exchange_rate)

    def add_security_movement(self, security_movement):
        if security_movement not in self.security_movements:
            self.security_movements.append(security_movement)
            logging.info("Added security movement to transaction %s: %s", self.transaction_number, security_movement)

    def validate_transaction(self, portfolio, product_collection):
        logging.debug("Validating transaction...")
        messages = []
        sufficient_funds = True

        if not portfolio:
            messages.append("The portfolio does not exist.")
            sufficient_funds = False

        if not portfolio.client_id:
            messages.append("The client does not exist.")
            sufficient_funds = False

        total_cost_per_currency = {}

        for movement in self.cash_movements:
            logging.debug(f"Validating cash movement for account {movement.cash_account_id} in {movement.transaction_currency}")
            try:
                cash_account = portfolio.get_account_by_currency(movement.transaction_currency)
                logging.debug(f"Found cash account {cash_account.cash_account_id} in currency {movement.transaction_currency}")
            except ValueError:
                try:
                    cash_account = portfolio.get_account_by_currency(portfolio.default_currency)
                    exchange_rate = 1 / movement.exchange_rate if movement.transaction_currency != portfolio.default_currency else 1.0
                    movement.amount_account_currency *= exchange_rate
                    logging.debug(f"Using default currency account {cash_account.cash_account_id} with exchange rate {exchange_rate}")
                except ValueError as e:
                    messages.append(str(e))
                    sufficient_funds = False
                    continue

            if movement.exchange_rate <= 0:
                messages.append(f"Invalid exchange rate for cash movement: {movement.exchange_rate}")
                sufficient_funds = False
                continue

            cost_in_account_currency = movement.amount_account_currency if movement.transaction_currency == cash_account.currency else movement.amount_account_currency * movement.exchange_rate
            cost_in_account_currency = -cost_in_account_currency

            if movement.transaction_currency not in total_cost_per_currency:
                total_cost_per_currency[movement.transaction_currency] = 0
            total_cost_per_currency[movement.transaction_currency] += cost_in_account_currency

        for currency, total_cost in total_cost_per_currency.items():
            try:
                cash_account = portfolio.get_account_by_currency(currency)
                logging.debug(f"Validating total cost in currency {currency} for account {cash_account.cash_account_id}")
            except ValueError:
                try:
                    cash_account = portfolio.get_account_by_currency(portfolio.default_currency)
                    logging.debug(f"Using default currency account {cash_account.cash_account_id} for total cost validation")
                except ValueError as e:
                    messages.append(str(e))
                    sufficient_funds = False
                    continue

            if cash_account.balance < total_cost:
                messages.append(f"Insufficient balance for the total transaction amount in {currency}. Account balance: {cash_account.balance}, Required: {total_cost}")
                sufficient_funds = False

        for movement in self.security_movements:
            logging.debug(f"Validating security movement for product {movement.product_id}")
            product = product_collection.search_product_id(movement.product_id)
            if not product:
                messages.append(f"The product {movement.product_id} does not exist.")
                sufficient_funds = False
                continue

            if movement.amount_nominal * movement.price < product.minimum_purchase_value:
                messages.append(f"The transaction value for product {movement.product_id} does not meet the minimum purchase value.")
                sufficient_funds = False

            if movement.amount_nominal % product.smallest_trading_unit != 0:
                messages.append(f"The transaction amount for product {movement.product_id} is not a multiple of the smallest trading unit.")
                sufficient_funds = False

            if hasattr(product, 'start_date') and hasattr(product, 'maturity_date'):
                if not (product.start_date <= self.transaction_date <= product.maturity_date):
                    messages.append(f"The transaction date for product {movement.product_id} is outside the valid date range ({product.start_date} to {product.maturity_date}).")
                    sufficient_funds = False

            total_holding = sum(
                h['amount'] for h in portfolio.securities_account.holdings
                if h['product'].instrument_id == movement.product_id
            )
            if movement.movement_type == MovementType.SECURITY_SELL and total_holding < movement.amount_nominal:
                messages.append(f"Insufficient holdings for product {movement.product_id}.")
                sufficient_funds = False

        logging.debug("Validation successful")
        return sufficient_funds, messages

# price classes

class CurrencyPrices:
    def __init__(self):
        self.prices = []

    def add_price(self, currency_id: str, date: date, price: float, counter_currency: str = DEFAULT_CURRENCY):
        new_price = (currency_id, date, price, counter_currency)
        if new_price in self.prices:
            logging.warning("Price for %s on %s already exists.", currency_id, date)
            return
        self.prices.append(new_price)
        logging.info("Added price for currency %s on %s", currency_id, date)

    def get_latest_price(self, currency_id: str, counter_currency: str = DEFAULT_CURRENCY):
        prices = [price for price in self.prices if price[0] == currency_id and price[3] == counter_currency]
        if not prices:
            # Try to find the reverse exchange rate
            reverse_prices = [price for price in self.prices if price[0] == counter_currency and price[3] == currency_id]
            if not reverse_prices:
                raise ValueError(f"No exchange rate available for {currency_id} to {counter_currency} or {counter_currency} to {currency_id}")
            return 1 / max(reverse_prices, key=lambda x: x[1])[2]
        return max(prices, key=lambda x: x[1])[2]

    def show_prices(self, currency_id: str, start_date: date = date.today(), end_date: date = date(2099, 12, 31), counter_currency: str = DEFAULT_CURRENCY):
        filtered_prices = [
            price for price in self.prices
            if price[0] == currency_id and
               price[3] == counter_currency and
               start_date <= price[1] <= end_date
        ]
        return filtered_prices

class ProductPrices:
    def __init__(self, product_collection):
        self.product_collection = product_collection

    def add_price(self, price_product_id, date, price, price_currency):
        product = self.product_collection.search_product_id(price_product_id)
        if product:
            if product.issue_currency != price_currency:
                error_msg = f'Error: Currency mismatch for {price_product_id}. Expected: {product.issue_currency}, got: {price_currency}'
                logging.error(error_msg)
                return error_msg
            product.add_price(date, price)
            success_msg = f'New price for {price_product_id} added'
            logging.info(success_msg)
            return success_msg
        else:
            error_msg = 'Error: Product not found'
            logging.error(error_msg)
            return error_msg

    def show_prices(self, product_id, start_date=date.today(), end_date=date(2099, 12, 31)):
        product = self.product_collection.search_product_id(product_id)
        if product:
            return [(d, p) for d, p in product.prices if start_date <= d <= end_date]
        return []
