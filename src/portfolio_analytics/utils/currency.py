"""Currency formatting helpers."""

from __future__ import annotations


def format_currency(amount: float, currency: str = "EUR", decimals: int = 2) -> str:
    """Format *amount* with a currency symbol and thousand separators."""
    symbols = {"EUR": "€", "USD": "$", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.{decimals}f}"


def format_pct(value: float, decimals: int = 2) -> str:
    """Format a ratio (0.0–1.0) as a percentage string."""
    return f"{value * 100:.{decimals}f}%"
