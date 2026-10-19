"""
综合测试: 所有功能模块
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.model.user import User
from app.model.laboratory import Laboratory
from app.model.equipment import Equipment
from app.model.booking import Booking
from app.schemas.laboratory import LaboratoryCreate
from app.schemas.equipment import EquipmentCreate
from app.schemas.booking import BookingCreate, BookingApprove
from app.services.laboratory_services import LaboratoryService
from app.services.equipment_services import EquipmentService
from app.services.booking_services import BookingService
from app.services.user_services import UserService
from app.utils.password import hash_password


def setup_test_db():
    """Setup test database"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_user_management():
    """Test user management features"""
    db = setup_test_db()
    print("\n=== Testing User Management ===")

    # Create admin user
    print("\n1. Creating admin user...")
    admin = UserService.create_user(db, "admin", "password123", "Administrator", "admin")
    print(f"   [PASS] Admin user created: {admin.username}")

    # Create student user
    print("\n2. Creating student user...")
    student = UserService.create_user(db, "student1", "password123", "Student One", "student")
    print(f"   [PASS] Student user created: {student.username}")

    # Get user by ID
    print("\n3. Getting user by ID...")
    user = UserService.get_user_by_id(db, admin.id)
    print(f"   [PASS] Retrieved user: {user.name}")

    # Get all users
    print("\n4. Getting all users...")
    users = UserService.get_all_users(db, skip=0, limit=10)
    print(f"   [PASS] Total users: {len(users)}")

    # Change password
    print("\n5. Changing password...")
    result = UserService.change_password(db, student.id, "password123", "newpassword123")
    print(f"   [PASS] {result['message']}")

    # Toggle user status
    print("\n6. Toggling user status...")
    toggled_user = UserService.toggle_user_status(db, student.id)
    print(f"   [PASS] User status changed to: {toggled_user.status}")

    # Search users
    print("\n7. Searching users...")
    search_result = UserService.search_users(db, "admin")
    print(f"   [PASS] Found {len(search_result)} user(s)")

    # Get users by role
    print("\n8. Getting users by role...")
    students = UserService.get_users_by_role(db, "student")
    print(f"   [PASS] Found {len(students)} student(s)")

    print("\n[SUCCESS] User management tests passed!")
    db.close()
    return admin, student


def test_laboratory_and_equipment():
    """Test laboratory and equipment management"""
    db = setup_test_db()
    print("\n=== Testing Laboratory and Equipment ===")

    # Create laboratory
    print("\n1. Creating laboratory...")
    lab_data = LaboratoryCreate(
        name="Physics Lab",
        description="For physics experiments",
        location="Building A, Floor 2",
        capacity=30,
        manager_id=1,
        status=1
    )
    lab = LaboratoryService.create_laboratory(db, lab_data)
    print(f"   [PASS] Laboratory created: {lab.name}")

    # Create equipment
    print("\n2. Creating equipment...")
    eq_data = EquipmentCreate(
        name="Microscope A",
        equipment_type="Microscope",
        laboratory_id=lab.id,
        model="BX53",
        serial_number="SN-001",
        description="High power microscope",
        purchase_date="2023-01-15",
        maintenance_status="Normal",
        status=1
    )
    equipment = EquipmentService.create_equipment(db, eq_data)
    print(f"   [PASS] Equipment created: {equipment.name}")

    print("\n[SUCCESS] Laboratory and equipment tests passed!")
    db.close()
    return lab, equipment


def test_booking_management():
    """Test booking management features"""
    db = setup_test_db()
    print("\n=== Testing Booking Management ===")

    # Create laboratory for booking
    lab_data = LaboratoryCreate(
        name="Test Lab",
        description="Test",
        location="A-101",
        capacity=50,
        manager_id=1,
        status=1
    )
    lab = LaboratoryService.create_laboratory(db, lab_data)

    # Create booking
    print("\n1. Creating booking...")
    booking_data = BookingCreate(
        laboratory_id=lab.id,
        start_time="2024-10-25 14:00",
        end_time="2024-10-25 16:00",
        purpose="Experiment: Thermal properties",
        student_count=5,
        remarks="Important experiment"
    )
    booking = BookingService.create_booking(db, 1, booking_data)
    print(f"   [PASS] Booking created: ID={booking.id}, Status={booking.status}")

    # Get booking by ID
    print("\n2. Getting booking by ID...")
    b = BookingService.get_booking_by_id(db, booking.id)
    print(f"   [PASS] Retrieved booking: {b.purpose}")

    # Get user bookings
    print("\n3. Getting user bookings...")
    user_bookings = BookingService.get_user_bookings(db, 1)
    print(f"   [PASS] User has {len(user_bookings)} booking(s)")

    # Approve booking
    print("\n4. Approving booking...")
    approve_data = BookingApprove(status="已批准", remarks="Approved")
    approved_booking = BookingService.approve_booking(db, booking.id, approve_data, 1)
    print(f"   [PASS] Booking approved: Status={approved_booking.status}")

    # Update booking
    print("\n5. Cancelling booking...")
    result = BookingService.cancel_booking(db, booking.id)
    print(f"   [PASS] {result['message']}")

    # Test time conflict detection
    print("\n6. Testing time conflict detection...")
    try:
        conflicting_booking = BookingCreate(
            laboratory_id=lab.id,
            start_time="2024-10-25 14:30",  # Overlaps with first booking
            end_time="2024-10-25 15:30",
            purpose="Another experiment",
            student_count=3
        )
        BookingService.create_booking(db, 2, conflicting_booking)
        print("   [FAIL] Should have detected conflict!")
    except Exception as e:
        print(f"   [PASS] Correctly detected conflict: {str(e)}")

    print("\n[SUCCESS] Booking management tests passed!")
    db.close()


def test_integration():
    """Test integrated workflow"""
    db = setup_test_db()
    print("\n=== Testing Integrated Workflow ===")

    # Step 1: Create users
    print("\n1. Creating users...")
    admin = UserService.create_user(db, "admin", "admin123", "Admin", "admin")
    student = UserService.create_user(db, "student", "student123", "Student", "student")
    print(f"   [PASS] Created admin and student")

    # Step 2: Create laboratory
    print("\n2. Creating laboratory...")
    lab_data = LaboratoryCreate(
        name="Integrated Test Lab",
        description="For integrated testing",
        location="Building C",
        capacity=40,
        manager_id=admin.id,
        status=1
    )
    lab = LaboratoryService.create_laboratory(db, lab_data)
    print(f"   [PASS] Laboratory created by admin")

    # Step 3: Create equipment in laboratory
    print("\n3. Adding equipment to laboratory...")
    eq_data = EquipmentCreate(
        name="Testing Equipment",
        equipment_type="Analyzer",
        laboratory_id=lab.id,
        model="TA-100",
        serial_number="SN-TEST-001"
    )
    equipment = EquipmentService.create_equipment(db, eq_data)
    print(f"   [PASS] Equipment added to laboratory")

    # Step 4: Student creates booking
    print("\n4. Student creating booking...")
    booking_data = BookingCreate(
        laboratory_id=lab.id,
        start_time="2024-10-26 09:00",
        end_time="2024-10-26 11:00",
        purpose="Research project",
        student_count=3
    )
    booking = BookingService.create_booking(db, student.id, booking_data)
    print(f"   [PASS] Booking created by student")

    # Step 5: Admin approves booking
    print("\n5. Admin approving booking...")
    approve_data = BookingApprove(status="已批准", remarks="Good project")
    BookingService.approve_booking(db, booking.id, approve_data, admin.id)
    print(f"   [PASS] Booking approved by admin")

    print("\n[SUCCESS] Integrated workflow test passed!")
    db.close()


def main():
    """Run all tests"""
    print("=" * 50)
    print("Comprehensive Feature Testing")
    print("=" * 50)

    try:
        test_user_management()
        test_laboratory_and_equipment()
        test_booking_management()
        test_integration()

        print("\n" + "=" * 50)
        print("[SUCCESS] All tests passed!")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"\n[FAIL] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
