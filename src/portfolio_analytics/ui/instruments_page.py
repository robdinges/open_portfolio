"""
Instruments page — list and detail view for all instruments.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from portfolio_analytics.domain.interfaces import PricingServiceBase
from portfolio_analytics.domain.models import Instrument
from portfolio_analytics.repositories.base import InstrumentRepository


def render(
    instrument_repo: InstrumentRepository,
    pricing_service: PricingServiceBase,
) -> None:
    """Draw the Instruments page."""

    st.header("Instruments")

    instruments = instrument_repo.list_all()
    if not instruments:
        st.info("No instruments registered.")
        return

    # --- List view -----------------------------------------------------
    rows = [
        {
            "ID": inst.id,
            "Name": inst.name,
            "Type": inst.type.value,
            "Currency": inst.currency,
        }
        for inst in instruments
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # --- Detail view ---------------------------------------------------
    st.subheader("Instrument Detail")
    selected_id = st.selectbox(
        "Select instrument",
        options=[inst.id for inst in instruments],
        format_func=lambda iid: next(
            (i.name for i in instruments if i.id == iid), iid
        ),
    )

    if selected_id:
        inst = instrument_repo.get(selected_id)
        if inst:
            st.json({
                "id": inst.id,
                "name": inst.name,
                "type": inst.type.value,
                "currency": inst.currency,
                "metadata": inst.metadata,
            })

            # Price lookup
            price_date = st.date_input("Price date", value=date.today())
            if st.button("Get Price"):
                try:
                    price = pricing_service.get_price(inst.id, price_date)
                    st.success(f"Price on {price_date}: {price:.4f} {inst.currency}")
                except ValueError as e:
                    st.error(str(e))
