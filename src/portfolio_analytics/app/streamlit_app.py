"""
Streamlit dashboard entry point.

Run with::

    PYTHONPATH=src streamlit run src/portfolio_analytics/app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from portfolio_analytics.app.dependencies import bootstrap

# Bootstrap once per session
if "container" not in st.session_state:
    st.session_state.container = bootstrap()

container = st.session_state.container
config = container.config

st.set_page_config(
    page_title=config.streamlit_page_title,
    layout="wide",
)

st.markdown(
        """
        <style>
            .stMetric {
                background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
                border: 1px solid #dbe4ff;
                border-radius: 12px;
                padding: 0.5rem 0.75rem;
            }
            h1, h2, h3 {
                letter-spacing: 0.2px;
            }
            .stTabs [data-baseweb="tab"] {
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
)

st.title(config.streamlit_page_title)

# Sidebar — portfolio selector
portfolios = container.portfolio_repo.list_by_client(
    container.client_repo.list_all()[0].id
) if container.client_repo.list_all() else []

if not portfolios:
    st.warning("No portfolios found. Generate demo data first.")
    st.stop()

portfolio_id = st.sidebar.selectbox(
    "Portfolio",
    options=[p.id for p in portfolios],
    format_func=lambda pid: next((p.name for p in portfolios if p.id == pid), pid),
)

# Sidebar — as-of date
as_of_date = st.sidebar.date_input("As-of date")
from datetime import datetime

as_of = datetime(as_of_date.year, as_of_date.month, as_of_date.day, 23, 59, 59)

# Navigation
page = st.sidebar.radio(
    "Page",
    options=[
        "Overview",
        "Bond Analytics",
        "Performance",
        "Risk",
        "Attribution",
        "Data Quality",
        "Instruments",
        "Transactions",
        "Static Data Editor",
    ],
)

# Route to the selected page
if page == "Overview":
    from portfolio_analytics.ui.portfolio_overview import render as render_overview
    render_overview(container.analytics_service, portfolio_id, as_of)

elif page == "Bond Analytics":
    from portfolio_analytics.ui.bond_analytics_page import render as render_bond_analytics
    render_bond_analytics(container.analytics_service, portfolio_id, as_of)

elif page == "Performance":
    from portfolio_analytics.ui.performance_page import render as render_performance
    render_performance(container.analytics_service, portfolio_id, as_of)

elif page == "Risk":
    from portfolio_analytics.ui.risk_page import render as render_risk
    render_risk(container.analytics_service, portfolio_id, as_of)

elif page == "Attribution":
    from portfolio_analytics.ui.attribution_page import render as render_attribution
    render_attribution(container.analytics_service, portfolio_id, as_of)

elif page == "Data Quality":
    from portfolio_analytics.ui.data_quality_page import render as render_data_quality
    render_data_quality(container.analytics_service, portfolio_id, as_of)

elif page == "Instruments":
    from portfolio_analytics.ui.instruments_page import render as render_instruments
    render_instruments(container.instrument_repo, container.pricing_service)

elif page == "Transactions":
    from portfolio_analytics.ui.transactions_page import render as render_transactions
    render_transactions(container.transaction_repo, portfolio_id)

elif page == "Static Data Editor":
    from portfolio_analytics.ui.static_data_editor import render as render_editor
    render_editor(container.instrument_repo)
