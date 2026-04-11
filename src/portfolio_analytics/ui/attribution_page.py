"""Attribution page — contribution by instrument and asset class."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_analytics.domain.interfaces import PortfolioAnalyticsServiceBase
from portfolio_analytics.utils.currency import format_pct


def render(
    analytics: PortfolioAnalyticsServiceBase,
    portfolio_id: str,
    as_of,
) -> None:
    """Render the attribution dashboard."""
    st.header("Attribution")
    report = analytics.get_attribution_report(portfolio_id, as_of)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("By Instrument")
        instrument_df = pd.DataFrame(
            [
                {
                    "Label": entry.label,
                    "Market Value": entry.market_value,
                    "Weight": format_pct(entry.weight),
                    "Unrealized P&L": entry.unrealized_pnl,
                    "P&L Contribution": format_pct(entry.pnl_contribution),
                }
                for entry in report.by_instrument
            ]
        )
        st.dataframe(instrument_df, width="stretch", hide_index=True)

    with col2:
        st.subheader("By Asset Class")
        asset_df = pd.DataFrame(
            [
                {
                    "Label": entry.label,
                    "Market Value": entry.market_value,
                    "Weight": format_pct(entry.weight),
                    "Unrealized P&L": entry.unrealized_pnl,
                    "P&L Contribution": format_pct(entry.pnl_contribution),
                }
                for entry in report.by_asset_class
            ]
        )
        st.dataframe(asset_df, width="stretch", hide_index=True)
