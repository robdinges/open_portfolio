"""Bond analytics page — clean/dirty price, accrual, yield, and duration."""

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
    """Render the bond analytics dashboard."""
    st.header("Bond Analytics")
    report = analytics.get_bond_analytics(portfolio_id, as_of)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Dirty Value", format_currency(report.total_dirty_value, report.currency))
    col2.metric("Accrued Interest", format_currency(report.total_accrued_interest, report.currency))
    col3.metric("Average YTM", format_pct(report.average_ytm))

    if not report.entries:
        st.info("No bond holdings found for the selected portfolio and date.")
        return

    rows = [
        {
            "Instrument": entry.instrument_name,
            "Qty": entry.quantity,
            "Clean": entry.clean_price,
            "Dirty": entry.dirty_price,
            "Accrued": entry.accrued_interest,
            "Coupon %": entry.coupon_rate,
            "Current Yield": format_pct(entry.current_yield),
            "YTM": format_pct(entry.simplified_ytm),
            "MacDur": entry.macaulay_duration,
            "ModDur": entry.modified_duration,
            "Convexity": entry.convexity,
            "Maturity": entry.maturity_date.date().isoformat() if entry.maturity_date else "",
            "Market Value": entry.market_value,
            "Ccy": entry.currency,
        }
        for entry in report.entries
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
