import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.model.booking import Booking
from app.model.laboratory import Laboratory
from app.model.user import User
from app.services.ai_tools import _list_my_bookings


class BookingQueryTests(unittest.TestCase):
    def test_active_query_excludes_cancelled_history(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()
        try:
            user = User(
                username="booking_query_user",
                password="hashed",
                name="Booking Query User",
                role="student",
                status=1,
            )
            laboratory = Laboratory(
                name="Query Lab",
                description="",
                location="A-101",
                capacity=10,
                manager_id=1,
                status=1,
            )
            db.add_all([user, laboratory])
            db.commit()
            db.refresh(user)
            db.refresh(laboratory)
            db.add_all([
                Booking(
                    user_id=user.id,
                    laboratory_id=laboratory.id,
                    start_time="2026-11-05 14:00",
                    end_time="2026-11-05 16:00",
                    purpose="active",
                    student_count=1,
                    status="待审核",
                ),
                Booking(
                    user_id=user.id,
                    laboratory_id=laboratory.id,
                    start_time="2026-11-06 14:00",
                    end_time="2026-11-06 16:00",
                    purpose="cancelled",
                    student_count=1,
                    status="已取消",
                ),
            ])
            db.commit()

            result = _list_my_bookings(db, user.id, "active", 50)
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["items"][0]["status"], "待审核")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
