import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.domain.booking.resolver import resolve_laboratory
from app.domain.booking.query import resolve_pending_booking_query
from app.services.ai_services import _emit_text_deltas
from app.model.laboratory import Laboratory
from app.services.agent_router import (
    AgentIntent,
    is_cancel_booking_request,
    route_request,
)


class AgentArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([
            Laboratory(name="化学实验室", location="深圳", capacity=1, manager_id=1, status=1),
            Laboratory(name="广州化学实验室", location="广州", capacity=2, manager_id=1, status=1),
            Laboratory(name="物理实验室", location="深圳", capacity=2, manager_id=1, status=1),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_exact_full_name_wins_over_containing_name(self):
        result = resolve_laboratory(self.db, "帮我预约化学实验室")
        self.assertFalse(result.ambiguous)
        self.assertEqual(result.laboratory.name, "化学实验室")
        self.assertEqual(result.method, "exact_name")

    def test_location_shorthand_is_ambiguous_only_when_needed(self):
        result = resolve_laboratory(self.db, "帮我预约广州实验室")
        self.assertFalse(result.ambiguous)
        self.assertEqual(result.laboratory.name, "广州化学实验室")

    def test_router_separates_query_and_create(self):
        self.assertEqual(route_request("现在还有哪些预约").intent, AgentIntent.BOOKING_QUERY)
        self.assertEqual(route_request("帮我预约化学实验室").intent, AgentIntent.BOOKING_CREATE)
        self.assertEqual(route_request("帮我取消我的预约").intent, AgentIntent.CANCEL_BOOKING)

    def test_cancel_with_laboratory_name_is_cancel_intent(self):
        text = "帮我取消广州化学实验室的预约"
        self.assertTrue(is_cancel_booking_request(text))
        self.assertEqual(route_request(text).intent, AgentIntent.CANCEL_BOOKING)

    def test_admin_pending_booking_query_is_not_create_intent(self):
        decision = route_request("目前其他用户有哪些需要审批的预约")
        self.assertEqual(decision.intent, AgentIntent.ADMIN_BOOKING_QUERY)

    def test_admin_booking_query_parses_today_window(self):
        decision = route_request(
            "今天有需要审批的预约吗",
            now=datetime(2026, 10, 29, 12, 0),
        )
        self.assertEqual(decision.intent, AgentIntent.ADMIN_BOOKING_QUERY)
        self.assertEqual(decision.parameters["time_label"], "今天")
        self.assertEqual(decision.parameters["time_from"], "2026-10-29 00:00")
        self.assertEqual(decision.parameters["time_to"], "2026-10-30 00:00")

    def test_admin_booking_query_parses_recent_month_window(self):
        query = resolve_pending_booking_query(
            "最近一个月有需要审批的预约吗",
            now=datetime(2026, 10, 29, 12, 0),
        )
        self.assertEqual(query.time_label, "最近一个月")
        self.assertEqual(query.time_from, "2026-09-29 00:00")
        self.assertEqual(query.time_to, "2026-10-30 00:00")

    def test_deterministic_response_emits_incremental_deltas(self):
        events = []
        _emit_text_deltas(events.append, "预约已提交，当前状态为待审核。", chunk_size=4)
        self.assertGreater(len(events), 1)
        self.assertEqual("".join(event["delta"] for event in events), "预约已提交，当前状态为待审核。")
        self.assertTrue(all(event["type"] == "delta" for event in events))

    def test_router_keeps_resource_query_out_of_booking_create(self):
        decision = route_request("帮我看看有哪些实验室和设备可以预约")
        self.assertEqual(decision.intent, AgentIntent.RESOURCE_QUERY)

    def test_router_only_resumes_when_workflow_context_exists(self):
        self.assertEqual(
            route_request("继续前面的预约", workflow_active=False).intent,
            AgentIntent.BOOKING_RESUME,
        )
        self.assertEqual(
            route_request("明天下午4点到6点", workflow_active=True).intent,
            AgentIntent.BOOKING_CREATE,
        )


if __name__ == "__main__":
    unittest.main()
