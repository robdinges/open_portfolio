from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderStatus(Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUBMITTED = "submitted"


@dataclass
class PlaceholderGap:
    gap_id: str
    title: str
    description: str
    fallback_behavior: str
    backlog_ref: str


@dataclass
class OrderDraft:
    draft_id: str
    status: OrderStatus
    payload: Dict[str, Any]
    created_at: str
    updated_at: str
    validity_date: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class InMemoryOrderRepository:
    """Simple in-memory draft storage used by the web flow.

    This keeps the first implementation self-contained while we migrate order
    drafts to persistent storage.
    """

    def __init__(self):
        self._drafts: Dict[str, OrderDraft] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"OD-{self._counter:06d}"

    def upsert_draft(
        self,
        payload: Dict[str, Any],
        draft_id: Optional[str] = None,
        status: OrderStatus = OrderStatus.DRAFT,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> OrderDraft:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        if draft_id and draft_id in self._drafts:
            draft = self._drafts[draft_id]
            draft.payload = payload
            draft.status = status
            draft.updated_at = now
            draft.validity_date = payload.get("validity_date")
            draft.errors = list(errors or [])
            draft.warnings = list(warnings or [])
            return draft

        new_draft = OrderDraft(
            draft_id=self._next_id(),
            status=status,
            payload=payload,
            created_at=now,
            updated_at=now,
            validity_date=payload.get("validity_date"),
            errors=list(errors or []),
            warnings=list(warnings or []),
        )
        self._drafts[new_draft.draft_id] = new_draft
        return new_draft

    def get_draft(self, draft_id: str) -> Optional[OrderDraft]:
        return self._drafts.get(draft_id)

    def set_status(self, draft_id: str, status: OrderStatus) -> Optional[OrderDraft]:
        draft = self._drafts.get(draft_id)
        if draft is None:
            return None
        draft.status = status
        draft.updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        return draft


class DatabaseOrderRepository:
    """Persistent draft storage backed by open_portfolio.database.Database."""

    def __init__(self, database):
        self._db = database
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"OD-{self._counter:06d}"

    def upsert_draft(
        self,
        payload: Dict[str, Any],
        draft_id: Optional[str] = None,
        status: OrderStatus = OrderStatus.DRAFT,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> OrderDraft:
        existing = self.get_draft(draft_id) if draft_id else None
        if existing is not None:
            created_at = existing.created_at
            draft_id_value = existing.draft_id
        else:
            created_at = datetime.now(UTC).isoformat(timespec="seconds")
            draft_id_value = draft_id or self._next_id()

        updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        portfolio_id = int(payload.get("portfolio_id") or 0)
        self._db.upsert_order_draft(
            draft_id=draft_id_value,
            portfolio_id=portfolio_id,
            status=status.value,
            payload=payload,
            errors=errors or [],
            warnings=warnings or [],
            created_at=created_at,
            updated_at=updated_at,
        )
        stored = self._db.get_order_draft(draft_id_value)
        if stored is None:
            raise ValueError("Kon conceptorder niet opslaan")
        return OrderDraft(
            draft_id=stored["draft_id"],
            status=OrderStatus(stored["status"]),
            payload=stored["payload"],
            created_at=stored["created_at"],
            updated_at=stored["updated_at"],
            validity_date=(stored["payload"] or {}).get("validity_date"),
            errors=stored["errors"],
            warnings=stored["warnings"],
        )

    def get_draft(self, draft_id: str) -> Optional[OrderDraft]:
        if not draft_id:
            return None
        stored = self._db.get_order_draft(draft_id)
        if stored is None:
            return None
        return OrderDraft(
            draft_id=stored["draft_id"],
            status=OrderStatus(stored["status"]),
            payload=stored["payload"],
            created_at=stored["created_at"],
            updated_at=stored["updated_at"],
            validity_date=(stored["payload"] or {}).get("validity_date"),
            errors=stored["errors"],
            warnings=stored["warnings"],
        )

    def set_status(self, draft_id: str, status: OrderStatus) -> Optional[OrderDraft]:
        draft = self.get_draft(draft_id)
        if draft is None:
            return None
        return self.upsert_draft(
            payload=draft.payload,
            draft_id=draft_id,
            status=status,
            errors=draft.errors,
            warnings=draft.warnings,
        )


ORDER_ENTRY_PLACEHOLDERS: List[PlaceholderGap] = [
    PlaceholderGap(
        gap_id="OE-GAP-001",
        title="Geavanceerde risicolimieten",
        description="Concentratie-, trader- en dagnotional-limieten zijn nog niet geactiveerd in de orderflow.",
        fallback_behavior="Alleen basischecks op saldo en positie blokkeren de order.",
        backlog_ref="BACKLOG.md Must/Should + ORDER_ENTRY_BACKLOG.md",
    ),
    PlaceholderGap(
        gap_id="OE-GAP-002",
        title="Uitgebreid kostenmodel",
        description="Broker-, beurs- en vaste componenten per venue ontbreken in de huidige kostenberekening.",
        fallback_behavior="Standaardkostenmethode wordt toegepast voor alle orders.",
        backlog_ref="BACKLOG.md Should + ORDER_ENTRY_BACKLOG.md",
    ),
    PlaceholderGap(
        gap_id="OE-GAP-003",
        title="Intraday prijsversheid",
        description="Prijsversheidscontrole voor market orders is nog niet beschikbaar.",
        fallback_behavior="Laatste beschikbare koers op of voor transactiedatum wordt gebruikt.",
        backlog_ref="BACKLOG.md Should + ORDER_ENTRY_BACKLOG.md",
    ),
    PlaceholderGap(
        gap_id="OE-GAP-004",
        title="Uitgebreide audit actor context",
        description="User-id, rol en goedkeuringsketen worden nog niet volledig vastgelegd in ordermetadata.",
        fallback_behavior="Orderstatus en timestamps worden vastgelegd zonder actor-details.",
        backlog_ref="BACKLOG.md Must + ORDER_ENTRY_BACKLOG.md",
    ),
]


def placeholder_messages() -> List[str]:
    messages: List[str] = []
    for gap in ORDER_ENTRY_PLACEHOLDERS:
        messages.append(
            f"{gap.gap_id}: {gap.title}. Fallback: {gap.fallback_behavior}"
        )
    return messages
