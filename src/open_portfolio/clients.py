from __future__ import annotations
from typing import List
from .accounts import Portfolio
import logging


class Client:
    """Represents a customer who owns one or more portfolios."""

    def __init__(self, client_id: int, name: str):
        self.client_id = client_id
        self.name = name
        self.portfolios: List[Portfolio] = []

    def add_portfolio(
        self,
        portfolio_id: int,
        default_currency: str = "EUR",
        cost_in_transaction_currency: bool = True,
        name: str = None,
    ) -> Portfolio:
        if any(p.portfolio_id == portfolio_id for p in self.portfolios):
            raise ValueError(f"Portfolio with ID {portfolio_id} already exists for client {self.client_id}.")
        portfolio = Portfolio(
            portfolio_id,
            name if name is not None else self.name,
            self.client_id,
            default_currency=default_currency,
            cost_in_transaction_currency=cost_in_transaction_currency,
        )
        self.portfolios.append(portfolio)
        logging.info("Added portfolio %s to client %s", portfolio_id, self.client_id)
        return portfolio
