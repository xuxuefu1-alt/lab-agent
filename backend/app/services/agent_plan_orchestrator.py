from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from app.services.agent_router import AgentIntent, IntentPlan, RouteDecision
from app.observability import record_plan_event


@dataclass(frozen=True)
class QueryPlanResult:
    tool_name: str
    rows: list[dict[str, Any]]
    raw: dict[str, Any]


@dataclass(frozen=True)
class ReadonlyPlanResult:
    plan_id: str
    mode: str
    steps: list[dict[str, Any]]
    failed_step: str | None = None


class AgentPlanOrchestrator:
    """Coordinate dependent multi-intent plans without owning domain writes."""

    SUPPORTED_QUERY_THEN_CANCEL = (AgentIntent.BOOKING_QUERY, AgentIntent.CANCEL_BOOKING)
    READONLY_INTENTS = frozenset({
        AgentIntent.BOOKING_QUERY,
        AgentIntent.RESOURCE_QUERY,
        AgentIntent.ADMIN_BOOKING_QUERY,
    })

    @classmethod
    def validate_plan(cls, plan: IntentPlan | None) -> str | None:
        """Return a stable validation error, or None when the plan is executable."""
        if plan is None:
            return "missing_plan"
        if not plan.steps:
            return "empty_plan"

        step_ids = [step.step_id for step in plan.steps]
        if len(step_ids) != len(set(step_ids)):
            return "duplicate_step_id"

        orders = [step.order for step in plan.steps]
        if len(orders) != len(set(orders)):
            return "duplicate_step_order"

        known_ids = set(step_ids)
        for step in plan.steps:
            if step.step_id in step.depends_on:
                return "self_dependency"
            if any(dependency not in known_ids for dependency in step.depends_on):
                return "unknown_dependency"

        visiting: set[str] = set()
        visited: set[str] = set()
        dependencies = {step.step_id: set(step.depends_on) for step in plan.steps}

        def visit(step_id: str) -> bool:
            if step_id in visiting:
                return False
            if step_id in visited:
                return True
            visiting.add(step_id)
            if not all(visit(dependency) for dependency in dependencies[step_id]):
                return False
            visiting.remove(step_id)
            visited.add(step_id)
            return True

        if not all(visit(step_id) for step_id in step_ids):
            return "cyclic_dependency"
        return None

    @classmethod
    def supports_query_then_cancel(cls, route: RouteDecision) -> bool:
        if route.intent is not AgentIntent.MULTI_INTENT or route.plan is None:
            return False
        if cls.validate_plan(route.plan) is not None:
            return False
        steps = sorted(route.plan.steps, key=lambda step: step.order)
        if tuple(step.intent for step in steps) != cls.SUPPORTED_QUERY_THEN_CANCEL:
            return False
        query_step, cancel_step = steps
        return (
            cancel_step.depends_on == [query_step.step_id]
            and cancel_step.requires_selection
            and cancel_step.requires_confirmation
        )

    @staticmethod
    def parse_selection(question: str, candidates: list[dict[str, Any]]) -> int | None:
        compact = re.sub(r"\s+", "", question or "")
        ordinal = re.search(r"第([1-9][0-9]*)条", compact)
        if ordinal:
            index = int(ordinal.group(1)) - 1
            if 0 <= index < len(candidates):
                return int(candidates[index].get("id"))

        direct = re.search(r"(?:预约|预订|编号|#)\s*([0-9]+)", question or "")
        if direct:
            booking_id = int(direct.group(1))
            if any(int(item.get("id")) == booking_id for item in candidates):
                return booking_id

        if compact.isdigit():
            booking_id = int(compact)
            if any(int(item.get("id")) == booking_id for item in candidates):
                return booking_id

        for item in candidates:
            name = (item.get("laboratory_name") or "").replace(" ", "")
            if name and name in compact:
                return int(item["id"])
        return None

    @classmethod
    def supports_readonly_plan(cls, route: RouteDecision) -> bool:
        if route.intent is not AgentIntent.MULTI_INTENT or route.plan is None:
            return False
        if cls.validate_plan(route.plan) is not None:
            return False
        if route.plan.mode not in {"sequential_independent", "parallel_independent"}:
            return False
        steps = sorted(route.plan.steps, key=lambda step: step.order)
        return all(
            step.intent in cls.READONLY_INTENTS
            and not step.requires_selection
            and not step.requires_confirmation
            and not step.depends_on
            for step in steps
        )

    def execute_readonly_plan(
        self,
        route: RouteDecision,
        step_callbacks: dict[str, Callable[[], QueryPlanResult]],
    ) -> ReadonlyPlanResult | None:
        if not self.supports_readonly_plan(route) or route.plan is None:
            return None

        plan_id = uuid4().hex
        mode = route.plan.mode
        steps = sorted(route.plan.steps, key=lambda step: step.order)
        record_plan_event(
            plan_id=plan_id,
            plan_mode=mode,
            plan_step="plan",
            plan_status="planned",
        )

        def run_step(step) -> tuple[Any, QueryPlanResult]:
            record_plan_event(
                plan_id=plan_id,
                plan_mode=mode,
                plan_step=step.step_id,
                plan_status="running",
            )
            try:
                result = step_callbacks[step.step_id]()
            except Exception as exc:
                result = QueryPlanResult(
                    tool_name=step.step_id,
                    rows=[],
                    raw={
                        "ok": False,
                        "error": "readonly_step_exception",
                        "error_type": type(exc).__name__,
                    },
                )
            return step, result

        if mode == "parallel_independent" and len(steps) > 1:
            with ThreadPoolExecutor(max_workers=len(steps)) as pool:
                futures = [pool.submit(run_step, step) for step in steps]
                completed = [future.result() for future in futures]
        else:
            completed = [run_step(step) for step in steps]

        output_steps: list[dict[str, Any]] = []
        failed_step = None
        for step, result in completed:
            ok = bool(result.raw.get("ok"))
            status = "completed" if ok else "failed"
            if not ok and failed_step is None:
                failed_step = step.step_id
            record_plan_event(
                plan_id=plan_id,
                plan_mode=mode,
                plan_step=step.step_id,
                plan_status=status,
                blocked_reason=None if ok else "readonly_step_failed",
            )
            output_steps.append({
                "step_id": step.step_id,
                "intent": step.intent.value,
                "tool_name": result.tool_name,
                "ok": ok,
                "rows": result.rows,
                "error": None if ok else result.raw.get("error"),
            })

        record_plan_event(
            plan_id=plan_id,
            plan_mode=mode,
            plan_step="plan",
            plan_status="failed" if failed_step else "completed",
            blocked_reason=failed_step,
        )
        return ReadonlyPlanResult(plan_id, mode, output_steps, failed_step)

    @staticmethod
    def build_state(
        route: RouteDecision,
        question: str,
        rows: list[dict[str, Any]],
        plan_id: str,
    ) -> dict[str, Any]:
        if route.plan is None:
            raise ValueError("A multi-intent plan is required")
        return {
            "plan_id": plan_id,
            "phase": "awaiting_selection",
            "retry_count": 0,
            "max_retries": 2,
            "plan_mode": route.plan.mode,
            "steps": [step.model_dump() for step in route.plan.steps],
            "current_step": "cancel_booking",
            "candidate_booking_ids": [int(item["id"]) for item in rows],
            "candidates": rows,
            "source_question": question,
        }

    def execute_query_then_cancel(
        self,
        route: RouteDecision,
        question: str,
        query_step: Callable[[], QueryPlanResult],
        save_state: Callable[[dict[str, Any]], None],
        persist_result: Callable[[dict[str, Any], str, str], dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not self.supports_query_then_cancel(route):
            return None

        plan_id = uuid4().hex
        plan_mode = route.plan.mode if route.plan else "unknown"
        record_plan_event(
            plan_id=plan_id,
            plan_mode=plan_mode,
            plan_step="query_bookings",
            plan_status="planned",
        )
        queried = query_step()
        if not queried.raw.get("ok"):
            record_plan_event(
                plan_id=plan_id,
                plan_mode=plan_mode,
                plan_step="query_bookings",
                plan_status="failed",
                blocked_reason="query_failed",
            )
            return persist_result(
                {
                    "content": queried.raw.get("error") or "查询步骤暂时失败。",
                    "tool_calls": [{"name": queried.tool_name, "ok": False}],
                    "blocks": [],
                    "confirmation_token": None,
                },
                queried.tool_name,
                "failed",
            )
        if not queried.rows:
            record_plan_event(
                plan_id=plan_id,
                plan_mode=plan_mode,
                plan_step="query_bookings",
                plan_status="completed",
            )
            return persist_result(
                {
                    "content": "当前没有可取消的预约。",
                    "tool_calls": [{"name": queried.tool_name, "ok": True}],
                    "blocks": [],
                    "confirmation_token": None,
                },
                queried.tool_name,
                "success",
            )

        save_state(self.build_state(route, question, queried.rows, plan_id))
        record_plan_event(
            plan_id=plan_id,
            plan_mode=plan_mode,
            plan_step="cancel_booking",
            plan_status="waiting_selection",
            selection_required=True,
            confirmation_required=True,
        )
        return persist_result(
            {
                "content": f"当前有 {len(queried.rows)} 条可取消预约，请选择要取消的预约。",
                "tool_calls": [{"name": queried.tool_name, "ok": True}],
                "blocks": [{
                    "type": "booking_cancellation_selection",
                    "title": "选择要取消的预约",
                    "items": queried.rows,
                    "count": len(queried.rows),
                    "next_action": "select_booking_for_cancellation",
                }],
                "confirmation_token": None,
            },
            queried.tool_name,
            "needs_selection",
        )
