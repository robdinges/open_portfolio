"""
Portfolio Overview page — KPIs, holdings table, allocation chart.

This module exposes ``render()`` which draws the main dashboard view
using the ``PortfolioAnalyticsServiceBase`` injected at startup.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from portfolio_analytics.domain.enums import AllocationDimension
from portfolio_analytics.domain.interfaces import PortfolioAnalyticsServiceBase
from portfolio_analytics.utils.currency import format_currency, format_pct


def render(
    analytics: PortfolioAnalyticsServiceBase,
    portfolio_id: str,
    as_of: Optional[datetime] = None,
) -> None:
    """Draw the Portfolio Overview page."""

    st.header("Portfolio Overview")

    overview = analytics.get_overview(portfolio_id, as_of)

    # --- KPI row -------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Portfolio Value", format_currency(overview.portfolio_value, overview.currency))
    col2.metric("Unrealised P&L", format_currency(overview.unrealized_pnl, overview.currency))
    col3.metric("# Holdings", len(overview.holdings))
    total_cash = sum(overview.cash_balances.values())
    col4.metric("Total Cash", format_currency(total_cash, overview.currency))

    # --- Holdings table ------------------------------------------------
    st.subheader("Holdings")
    if overview.holdings:
        rows = [
            {
                "Instrument": h.instrument_name,
                "Type": h.instrument_type.value,
                "Qty": h.quantity,
                "Avg Cost": round(h.average_cost, 2),
                "Mkt Price": round(h.market_price, 2),
                "Mkt Value": round(h.market_value, 2),
                "Cost Basis": round(h.cost_basis, 2),
                "P&L": round(h.unrealized_pnl, 2),
                "Alloc %": format_pct(h.allocation_pct),
                "Ccy": h.currency,
            }
            for h in overview.holdings
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No holdings found.")

    # --- Allocation chart ----------------------------------------------
    st.subheader("Asset Class Allocation")
    allocation = analytics.get_allocation(
        portfolio_id, AllocationDimension.ASSET_CLASS, as_of
    )
    if allocation:
        alloc_df = pd.DataFrame(
            [{"Asset Class": a.label, "Value": a.market_value} for a in allocation]
        )
        st.bar_chart(alloc_df.set_index("Asset Class"))
    else:
        st.info("No allocation data.")

    # --- Cash balances -------------------------------------------------
    st.subheader("Cash Balances")
    if overview.cash_balances:
        cash_df = pd.DataFrame(
            [
                {"Currency": ccy, "Balance": round(bal, 2)}
                for ccy, bal in overview.cash_balances.items()
            ]
        )
        st.dataframe(cash_df, use_container_width=True, hide_index=True)
