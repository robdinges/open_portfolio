from typing import List, Dict
from .accounts import Portfolio
from .enums import MovementType


class PortfolioAnalytics:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def get_holdings_progress(self, product_id: int) -> List[Dict]:
        holdings_progress: List[Dict] = []
        changes = set()
        # find product holdings
        for holding in self.portfolio.securities_account.holdings:
            prod = holding["product"]
            if prod.instrument_id != product_id:
                continue
            amount = 0
            for tx in prod.transactions:
                for mv in tx.security_movements:
                    if mv.product_id == product_id:
                        changes.add(mv.transaction_date)
                        if mv.movement_type == MovementType.SECURITY_BUY:
                            amount += mv.amount_nominal
                        else:
                            amount -= mv.amount_nominal
            for price_date, _ in prod.prices:
                changes.add(price_date)
        for date_ in sorted(changes):
            price = prod.get_price(date_)
            # compute amount at date
            amt = 0
            for tx in prod.transactions:
                for mv in tx.security_movements:
                    if mv.transaction_date <= date_ and mv.product_id == product_id:
                        if mv.movement_type == MovementType.SECURITY_BUY:
                            amt += mv.amount_nominal
                        else:
                            amt -= mv.amount_nominal
            value = amt * price if price is not None else 0
            holdings_progress.append({"Date": date_, "Amount": amt, "Price": price, "Value": value})
        return holdings_progress
