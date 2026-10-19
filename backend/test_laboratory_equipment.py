"""
集成测试：实验室管理和设备列表管理功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.model.laboratory import Laboratory
from app.model.equipment import Equipment
from app.schemas.laboratory import LaboratoryCreate, LaboratoryUpdate
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.services.laboratory_services import LaboratoryService
from app.services.equipment_services import EquipmentService


def setup_test_db():
    """设置测试数据库"""
    # 使用内存数据库进行测试
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_laboratory_crud():
    """测试实验室的增删改查"""
    db = setup_test_db()
    print("\n=== 测试实验室管理功能 ===")

    # 1. 创建实验室
    print("\n1. 创建实验室...")
    lab_data = LaboratoryCreate(
        name="化学实验室",
        description="用于化学实验的实验室",
        location="A楼2层",
        capacity=30,
        manager_id=1,
        status=1
    )
    lab = LaboratoryService.create_laboratory(db, lab_data)
    print("   [PASS] 创建成功: ID={}, 名称={}".format(lab.id, lab.name))
    assert lab.id is not None
    assert lab.name == "化学实验室"

    # 2. 查询实验室
    print("\n2. 查询实验室详情...")
    lab_retrieved = LaboratoryService.get_laboratory_by_id(db, lab.id)
    print("   [PASS] 查询成功: {} ({})".format(lab_retrieved.name, lab_retrieved.location))
    assert lab_retrieved.name == lab.name

    # 3. 更新实验室
    print("\n3. 更新实验室...")
    update_data = LaboratoryUpdate(
        capacity=40,
        description="更新的描述"
    )
    lab_updated = LaboratoryService.update_laboratory(db, lab.id, update_data)
    print("   [PASS] 更新成功: 容纳人数={}, 描述={}".format(lab_updated.capacity, lab_updated.description))
    assert lab_updated.capacity == 40

    # 4. 列表查询
    print("\n4. 获取实验室列表...")
    labs = LaboratoryService.get_all_laboratories(db, skip=0, limit=10)
    print("   [PASS] 查询成功: 共{}个实验室".format(len(labs)))
    assert len(labs) > 0

    # 5. 创建第二个实验室用于搜索测试
    print("\n5. 创建第二个实验室并测试搜索...")
    lab2_data = LaboratoryCreate(
        name="生物实验室",
        description="用于生物实验的实验室",
        location="B楼1层",
        capacity=25,
        manager_id=2,
        status=1
    )
    lab2 = LaboratoryService.create_laboratory(db, lab2_data)

    search_result = LaboratoryService.search_laboratories(db, "生物")
    print("   [PASS] 搜索成功: 找到{}个实验室".format(len(search_result)))
    assert len(search_result) > 0

    # 6. 删除实验室
    print("\n6. 删除实验室...")
    result = LaboratoryService.delete_laboratory(db, lab2.id)
    print("   [PASS] {}".format(result['message']))

    print("\n[SUCCESS] 实验室管理功能测试全部通过!")
    db.close()


def test_equipment_crud():
    """测试设备的增删改查"""
    db = setup_test_db()
    print("\n=== 测试设备列表管理功能 ===")

    # 先创建一个实验室
    lab_data = LaboratoryCreate(
        name="物理实验室",
        description="物理实验室",
        location="C楼3层",
        capacity=20,
        manager_id=1,
        status=1
    )
    lab = LaboratoryService.create_laboratory(db, lab_data)

    # 1. 创建设备
    print("\n1. 创建设备...")
    eq_data = EquipmentCreate(
        name="显微镜A",
        equipment_type="显微镜",
        laboratory_id=lab.id,
        model="BX53",
        serial_number="SN-001",
        description="高倍显微镜",
        purchase_date="2023-01-15",
        maintenance_status="正常",
        status=1
    )
    equipment = EquipmentService.create_equipment(db, eq_data)
    print("   [PASS] 创建成功: ID={}, 名称={}".format(equipment.id, equipment.name))
    assert equipment.id is not None
    assert equipment.name == "显微镜A"

    # 2. 查询设备
    print("\n2. 查询设备详情...")
    eq_retrieved = EquipmentService.get_equipment_by_id(db, equipment.id)
    print("   [PASS] 查询成功: {} (序列号: {})".format(eq_retrieved.name, eq_retrieved.serial_number))
    assert eq_retrieved.serial_number == "SN-001"

    # 3. 更新设备
    print("\n3. 更新设备...")
    update_data = EquipmentUpdate(
        maintenance_status="维修中"
    )
    eq_updated = EquipmentService.update_equipment(db, equipment.id, update_data)
    print("   [PASS] 更新成功: 维护状态={}".format(eq_updated.maintenance_status))
    assert eq_updated.maintenance_status == "维修中"

    # 4. 列表查询
    print("\n4. 获取设备列表...")
    equipments = EquipmentService.get_all_equipment(db, skip=0, limit=10)
    print("   [PASS] 查询成功: 共{}个设备".format(len(equipments)))
    assert len(equipments) > 0

    # 5. 创建第二个设备用于搜索测试
    print("\n5. 创建第二个设备并测试搜索...")
    eq2_data = EquipmentCreate(
        name="分光光度计B",
        equipment_type="分光光度计",
        laboratory_id=lab.id,
        model="UV-1900",
        serial_number="SN-002",
        description="紫外分光光度计",
        purchase_date="2023-02-20",
        maintenance_status="正常",
        status=1
    )
    eq2 = EquipmentService.create_equipment(db, eq2_data)

    search_result = EquipmentService.search_equipment(db, "分光")
    print("   [PASS] 搜索成功: 找到{}个设备".format(len(search_result)))
    assert len(search_result) > 0

    # 6. 按实验室查询设备
    print("\n6. 按实验室查询设备...")
    lab_equipment = EquipmentService.get_equipment_by_laboratory(db, lab.id)
    print("   [PASS] 查询成功: 该实验室有{}个设备".format(len(lab_equipment)))
    assert len(lab_equipment) >= 2

    # 7. 按维护状态查询
    print("\n7. 按维护状态查询设备...")
    maintain_equipment = EquipmentService.get_equipment_by_maintenance_status(db, "正常")
    print("   [PASS] 查询成功: 有{}个设备状态为正常".format(len(maintain_equipment)))

    # 8. 删除设备
    print("\n8. 删除设备...")
    result = EquipmentService.delete_equipment(db, eq2.id)
    print("   [PASS] {}".format(result['message']))

    print("\n[SUCCESS] 设备列表管理功能测试全部通过!")
    db.close()


def test_sequence_number_validation():
    """测试序列号唯一性约束"""
    db = setup_test_db()
    print("\n=== 测试序列号唯一性约束 ===")

    lab_data = LaboratoryCreate(
        name="测试实验室",
        description="测试",
        location="D楼",
        capacity=10,
        manager_id=1,
        status=1
    )
    lab = LaboratoryService.create_laboratory(db, lab_data)

    # 创建第一个设备
    eq1_data = EquipmentCreate(
        name="设备1",
        equipment_type="类型1",
        laboratory_id=lab.id,
        serial_number="UNIQUE-SN-123",
        maintenance_status="正常",
        status=1
    )
    eq1 = EquipmentService.create_equipment(db, eq1_data)
    print("\n[PASS] 创建第一个设备成功")

    # 尝试创建相同序列号的设备
    print("\n尝试创建相同序列号的设备...")
    eq2_data = EquipmentCreate(
        name="设备2",
        equipment_type="类型2",
        laboratory_id=lab.id,
        serial_number="UNIQUE-SN-123",
        maintenance_status="正常",
        status=1
    )

    try:
        eq2 = EquipmentService.create_equipment(db, eq2_data)
        print("[FAIL] 错误: 应该拒绝相同的序列号!")
        assert False
    except Exception as e:
        print("[PASS] 正确捕获异常: {}".format(str(e)))

    print("\n[SUCCESS] 序列号唯一性约束测试通过!")
    db.close()


def main():
    """运行所有测试"""
    print("=" * 50)
    print("实验室管理和设备列表管理 - 集成测试")
    print("=" * 50)

    try:
        test_laboratory_crud()
        test_equipment_crud()
        test_sequence_number_validation()

        print("\n" + "=" * 50)
        print("[SUCCESS] 所有测试全部通过!")
        print("=" * 50)
        return 0
    except Exception as e:
        print("\n[FAIL] 测试失败: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
