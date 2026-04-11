"""
Transactions page — filterable transaction ledger.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_analytics.domain.enums import TransactionType
from portfolio_analytics.repositories.base import TransactionRepository


def render(
    transaction_repo: TransactionRepository,
    portfolio_id: str,
) -> None:
    """Draw the Transactions page with filters."""

    st.header("Transactions")

    txs = transaction_repo.list_by_portfolio(portfolio_id)
    if not txs:
        st.info("No transactions found.")
        return

    # --- Filters -------------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        type_filter = st.multiselect(
            "Transaction type",
            options=[t.value for t in TransactionType],
            default=[t.value for t in TransactionType],
        )
    with col2:
        currency_filter = st.multiselect(
            "Currency",
            options=sorted({tx.currency for tx in txs}),
            default=sorted({tx.currency for tx in txs}),
        )

    filtered = [
        tx
        for tx in txs
        if tx.type.value in type_filter and tx.currency in currency_filter
    ]

    # --- Table ---------------------------------------------------------
    rows = [
        {
            "Date": tx.timestamp.strftime("%Y-%m-%d %H:%M"),
            "Type": tx.type.value,
            "Instrument": tx.instrument_id or "—",
            "Qty": tx.quantity,
            "Price": tx.price,
            "Amount": round(tx.amount, 2),
            "Ccy": tx.currency,
        }
        for tx in reversed(filtered)  # newest first
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(txs)} transactions")
