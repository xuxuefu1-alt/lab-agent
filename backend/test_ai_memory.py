import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.model.ai_conversation import AiConversation
from app.model.ai_message import AiMessage
from app.model.ai_workflow_state import AiWorkflowState
from app.model.user import User
from app.services import ai_memory_service


class AiMemoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(
            username="memory_test_user",
            password="hashed",
            name="Memory Test",
            role="student",
            status=1,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.conversation = AiConversation(
            user_id=self.user.id,
            client_key="memory-test",
            status="active",
        )
        self.db.add(self.conversation)
        self.db.commit()
        self.db.refresh(self.conversation)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_workflow_state_contains_resume_metadata(self):
        workflow = ai_memory_service.save_workflow_state(
            self.db,
            self.conversation,
            self.user,
            "create_booking",
            {
                "booking": {
                    "laboratory_id": 3,
                    "start_time": "2026-11-05 14:00",
                    "end_time": "2026-11-05 16:00",
                }
            },
        )
        self.db.commit()
        payload = json.loads(workflow.state_json)
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["phase"], "collecting_requirements")
        self.assertFalse(payload["completion"]["equipment"])
        self.assertNotIn("equipment", payload["missing_fields"])
        self.assertEqual(payload["policy_version"], "booking-policy-v2")

    def test_summary_is_bounded_and_marked_as_context(self):
        for index in range(max(12, settings.AI_CONTEXT_SUMMARY_TRIGGER_MESSAGES)):
            ai_memory_service.append_message(
                self.db,
                self.conversation,
                self.user.id,
                "user" if index % 2 == 0 else "assistant",
                f"第 {index} 条对话内容，用于验证摘要长度和上下文恢复。",
            )
        self.db.commit()
        summary = ai_memory_service.refresh_conversation_summary(self.db, self.conversation)
        self.assertIsNotNone(summary)
        self.assertLessEqual(len(summary), settings.AI_CONTEXT_SUMMARY_CHAR_BUDGET)
        context = ai_memory_service.build_summary_context(self.conversation)
        self.assertIn("untrusted conversation data", context)


if __name__ == "__main__":
    unittest.main()
