"""Performance page — return series and per-holding performance."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_analytics.domain.interfaces import PortfolioAnalyticsServiceBase
from portfolio_analytics.utils.currency import format_currency, format_pct


def render(
    analytics: PortfolioAnalyticsServiceBase,
    portfolio_id: str,
    as_of,
) -> None:
    """Render the performance dashboard."""
    st.header("Performance")
    lookback_days = st.selectbox("Lookback window", [63, 126, 252, 504], index=2)
    report = analytics.get_performance_report(portfolio_id, as_of, lookback_days)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Return", format_pct(report.total_return))
    col2.metric("Annualized Return", format_pct(report.annualized_return))
    col3.metric("Money-Weighted", format_pct(report.money_weighted_return))
    col4.metric("Time-Weighted", format_pct(report.time_weighted_return))

    st.subheader("Portfolio Value")
    series_df = pd.DataFrame(
        [{"Date": point.timestamp, "Portfolio Value": point.portfolio_value} for point in report.series]
    ).set_index("Date")
    st.line_chart(series_df, width="stretch")

    st.subheader("Holding Performance")
    rows = [
        {
            "Instrument": holding.instrument_name,
            "Type": holding.instrument_type.value,
            "Start Price": holding.start_price,
            "End Price": holding.end_price,
            "Total Return": format_pct(holding.total_return),
            "Annualized": format_pct(holding.annualized_return),
            "Weight": format_pct(holding.weight),
            "P&L Contribution": format_pct(holding.pnl_contribution),
        }
        for holding in report.holdings
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
