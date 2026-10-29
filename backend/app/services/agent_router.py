from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import re
from datetime import datetime

from app.services.booking_workflow import (
    is_booking_query_intent,
    is_booking_resume_intent,
    is_create_booking_intent,
    is_resource_query_intent,
)
from app.domain.booking.query import resolve_pending_booking_query


class AgentIntent(StrEnum):
    CANCEL_BOOKING = "cancel_booking"
    ADMIN_BOOKING_QUERY = "admin_booking_query"
    BOOKING_QUERY = "booking_query"
    RESOURCE_QUERY = "resource_query"
    BOOKING_RESUME = "booking_resume"
    BOOKING_CREATE = "booking_create"
    GENERAL = "general"


@dataclass(frozen=True)
class RouteDecision:
    intent: AgentIntent
    confidence: float
    deterministic: bool
    parameters: dict[str, object] | None = None


def is_cancel_booking_request(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text or "").casefold()
    if any(value in normalized for value in ("取消预约", "取消预订", "撤销预约", "撤销预订")):
        return True
    return "取消" in normalized and any(
        value in normalized for value in ("预约", "预订")
    )


def is_admin_booking_query_request(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text or "").casefold()
    return any(
        phrase in normalized
        for phrase in (
            "有哪些需要审批",
            "有哪些待审批",
            "有哪些待审核",
            "需要审批的预约",
            "待审批预约",
            "待审核预约",
            "其他用户有哪些预约",
            "其他用户的预约",
            "用户的预约",
        )
    )


def route_request(
    text: str,
    workflow_active: bool = False,
    now: datetime | None = None,
) -> RouteDecision:
    normalized = (text or "").strip()
    if is_cancel_booking_request(normalized):
        return RouteDecision(AgentIntent.CANCEL_BOOKING, 1.0, True)
    if is_admin_booking_query_request(normalized):
        return RouteDecision(
            AgentIntent.ADMIN_BOOKING_QUERY,
            1.0,
            True,
            asdict(resolve_pending_booking_query(normalized, now=now)),
        )
    if is_booking_query_intent(normalized):
        return RouteDecision(AgentIntent.BOOKING_QUERY, 1.0, True)
    if is_resource_query_intent(normalized):
        return RouteDecision(AgentIntent.RESOURCE_QUERY, 1.0, True)
    if is_booking_resume_intent(normalized):
        return RouteDecision(AgentIntent.BOOKING_RESUME, 1.0, True)
    if is_create_booking_intent(normalized) or (workflow_active and normalized):
        return RouteDecision(AgentIntent.BOOKING_CREATE, 0.95, True)
    return RouteDecision(AgentIntent.GENERAL, 0.5, False)
