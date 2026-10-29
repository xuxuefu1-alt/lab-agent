from datetime import datetime
from types import SimpleNamespace
import unittest

from app.services.booking_workflow import (
    is_booking_query_intent,
    is_create_booking_intent,
    _parse_date,
    _parse_time_range,
    _equipment_query_score,
)
from app.services.booking_policy import is_standard_booking_slot


class BookingWorkflowParsingTests(unittest.TestCase):
    def test_parse_one_week_after(self):
        now = datetime(2026, 10, 29, 9, 0)
        self.assertEqual(
            _parse_date("一周后的下午1点到2点", now).isoformat(),
            "2026-11-05",
        )

    def test_parse_meridiem_time_range(self):
        self.assertEqual(
            _parse_time_range("一周后的下午1点到2点"),
            (13, 0, 14, 0),
        )

    def test_reject_non_standard_slot(self):
        self.assertFalse(is_standard_booking_slot((13, 0, 14, 0)))
        self.assertFalse(is_standard_booking_slot((1, 0, 2, 0)))
        self.assertTrue(is_standard_booking_slot((14, 0, 16, 0)))

    def test_booking_query_is_not_create_intent(self):
        self.assertTrue(is_booking_query_intent("现在还有哪些预约"))
        self.assertFalse(is_create_booking_intent("现在还有哪些预约"))
        self.assertTrue(is_create_booking_intent("帮我预约医学实验室"))

    def test_equipment_matching_supports_resume_after_missing_time(self):
        equipment = SimpleNamespace(
            name="化学显微镜",
            equipment_type="显微镜",
            model=None,
        )
        self.assertGreater(
            _equipment_query_score("化学显微镜", equipment),
            0.9,
        )


if __name__ == "__main__":
    unittest.main()
