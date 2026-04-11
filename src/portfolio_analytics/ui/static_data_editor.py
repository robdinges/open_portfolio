"""
Static Data Editor — edit instrument metadata JSON.
"""

from __future__ import annotations

import json

import streamlit as st

from portfolio_analytics.domain.models import Instrument
from portfolio_analytics.repositories.base import InstrumentRepository


def render(instrument_repo: InstrumentRepository) -> None:
    """Draw the metadata editor page."""

    st.header("Static Data Editor")

    instruments = instrument_repo.list_all()
    if not instruments:
        st.info("No instruments to edit.")
        return

    selected_id = st.selectbox(
        "Select instrument",
        options=[inst.id for inst in instruments],
        format_func=lambda iid: next(
            (i.name for i in instruments if i.id == iid), iid
        ),
    )

    if not selected_id:
        return

    inst = instrument_repo.get(selected_id)
    if inst is None:
        st.error("Instrument not found.")
        return

    st.subheader(f"Editing: {inst.name}")
    st.text(f"ID: {inst.id}  |  Type: {inst.type.value}  |  Ccy: {inst.currency}")

    # JSON editor
    current_json = json.dumps(inst.metadata, indent=2)
    edited_json = st.text_area("Metadata (JSON)", value=current_json, height=250)

    if st.button("Save"):
        try:
            new_metadata = json.loads(edited_json)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            return

        updated = Instrument(
            id=inst.id,
            name=inst.name,
            type=inst.type,
            currency=inst.currency,
            metadata=new_metadata,
        )
        instrument_repo.save(updated)
        st.success("Metadata saved.")
