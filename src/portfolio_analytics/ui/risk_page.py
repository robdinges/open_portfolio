"""Risk page — volatility, Sharpe, drawdown, VaR, and correlation."""

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
    """Render the risk dashboard."""
    st.header("Risk")
    lookback_days = st.selectbox("Risk lookback window", [63, 126, 252, 504], index=2)
    report = analytics.get_risk_metrics(portfolio_id, as_of, lookback_days)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Daily Volatility", format_pct(report.daily_volatility))
    col2.metric("Annualized Volatility", format_pct(report.annualized_volatility))
    col3.metric("Sharpe Ratio", f"{report.sharpe_ratio:.2f}")
    col4.metric("Max Drawdown", format_pct(report.max_drawdown))

    col5, col6, col7 = st.columns(3)
    col5.metric("VaR 95%", format_pct(report.var_95))
    col6.metric("CVaR 95%", format_pct(report.cvar_95))
    col7.metric("Concentration", f"{report.concentration_index:.3f}")

    st.subheader("Correlation Matrix")
    if report.correlation_matrix:
        corr_df = pd.DataFrame(report.correlation_matrix)
        st.dataframe(corr_df, width="stretch")
        st.subheader("Average Correlation by Instrument")
        avg_corr = corr_df.mean(axis=1).to_frame(name="Avg Correlation")
        st.bar_chart(avg_corr, width="stretch")
    else:
        st.info("Not enough return history to calculate correlation.")
