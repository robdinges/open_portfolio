"""Data quality page — completeness and missing-field diagnostics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from portfolio_analytics.domain.interfaces import PortfolioAnalyticsServiceBase


def render(
    analytics: PortfolioAnalyticsServiceBase,
    portfolio_id: str,
    as_of,
) -> None:
    """Render the data-quality dashboard."""
    st.header("Data Quality")
    report = analytics.get_data_quality_report(portfolio_id, as_of)

    st.metric("Coverage", f"{report.coverage_pct:.2f}%")

    if not report.issues:
        st.success("No data-quality issues found for the current holdings.")
        return

    issue_df = pd.DataFrame(
        [
            {
                "Instrument": issue.instrument_name,
                "Severity": issue.severity,
                "Field": issue.field_name,
                "Message": issue.message,
            }
            for issue in report.issues
        ]
    )
    st.dataframe(issue_df, width="stretch", hide_index=True)
