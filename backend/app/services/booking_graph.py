from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.model.user import User
from app.services.ai_tools import build_tools
from app.services.booking_workflow import is_booking_resume_intent, resolve_booking_request


class BookingGraphState(TypedDict, total=False):
    question: str
    booking_draft: dict[str, Any]
    result: dict[str, Any]


def build_booking_graph(db: Session, current_user: User, checkpointer):
    def resolve_and_prepare(state: BookingGraphState) -> dict[str, Any]:
        question = state.get("question", "")
        draft = state.get("booking_draft") or {}
        resolution = resolve_booking_request(
            db,
            question,
            existing_draft=draft,
            workflow_active=True,
            resume_requested=is_booking_resume_intent(question),
        )
        next_draft = resolution.get("draft") or draft
        if not resolution.get("handled"):
            return {"booking_draft": next_draft, "result": {"handled": False}}
        if not resolution.get("ready"):
            return {
                "booking_draft": next_draft,
                "result": {
                    "handled": True,
                    "content": resolution["message"],
                    "tool_calls": [],
                    "blocks": [],
                    "confirmation_token": None,
                    "reason": resolution.get("reason"),
                },
            }

        prepare_tool = next(
            tool for tool in build_tools(db, current_user) if tool.name == "prepare_create_booking"
        )
        raw_result = prepare_tool.invoke(
            {
                "laboratory_id": resolution["laboratory_id"],
                "equipment_ids": resolution["equipment_ids"],
                "start_time": resolution["start_time"],
                "end_time": resolution["end_time"],
                "purpose": resolution["purpose"],
                "student_count": resolution["student_count"],
            }
        )
        tool_result = json.loads(raw_result)
        if not tool_result.get("ok"):
            return {
                "booking_draft": next_draft,
                "result": {
                    "handled": True,
                    "content": tool_result.get("error") or "当前时间段暂不可预约，请换一个时间段。",
                    "tool_calls": [{"name": "prepare_create_booking", "ok": False}],
                    "blocks": [],
                    "confirmation_token": None,
                },
            }

        data = tool_result.get("data") or {}
        booking = data.get("booking") or {}
        token = data.get("confirmation_token")
        return {
            "booking_draft": {
                **next_draft,
                "laboratory_id": booking.get("laboratory_id"),
                "laboratory_name": booking.get("laboratory_name"),
                "start_time": booking.get("start_time"),
                "end_time": booking.get("end_time"),
            },
            "result": {
                "handled": True,
                "content": "请确认预约信息。",
                "tool_calls": [{"name": "prepare_create_booking", "ok": True}],
                "blocks": [{
                    "type": "booking_confirmation",
                    "title": "请确认预约",
                    "status": data.get("status", "pending_confirmation"),
                    "booking": booking,
                    "count": 1,
                }],
                "confirmation_token": token,
                "booking": booking,
            },
        }

    graph = StateGraph(BookingGraphState)
    graph.add_node("resolve_and_prepare", resolve_and_prepare)
    graph.add_edge(START, "resolve_and_prepare")
    graph.add_edge("resolve_and_prepare", END)
    return graph.compile(checkpointer=checkpointer)
