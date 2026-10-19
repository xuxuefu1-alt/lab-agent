from sqlalchemy.orm import Session
from app.model.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.common.exceptions import BusinessExceptions


class EquipmentService:
    @staticmethod
    def create_equipment(db: Session, equipment: EquipmentCreate) -> Equipment:
        """创建设备"""
        # 检查序列号是否已存在
        if equipment.serial_number:
            existing = db.query(Equipment).filter(
                Equipment.serial_number == equipment.serial_number
            ).first()
            if existing:
                raise BusinessExceptions("序列号已存在")

        db_equipment = Equipment(
            name=equipment.name,
            equipment_type=equipment.equipment_type,
            laboratory_id=equipment.laboratory_id,
            model=equipment.model,
            serial_number=equipment.serial_number,
            description=equipment.description,
            purchase_date=equipment.purchase_date,
            maintenance_status=equipment.maintenance_status,
            status=equipment.status,
        )
        db.add(db_equipment)
        db.commit()
        db.refresh(db_equipment)
        return db_equipment

    @staticmethod
    def get_equipment_by_id(db: Session, equipment_id: int) -> Equipment:
        """根据ID获取设备"""
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise BusinessExceptions("设备不存在")
        return equipment

    @staticmethod
    def get_all_equipment(db: Session, skip: int = 0, limit: int = 10) -> list[Equipment]:
        """获取所有设备列表"""
        return db.query(Equipment).offset(skip).limit(limit).all()

    @staticmethod
    def get_equipment_count(db: Session) -> int:
        """获取设备总数"""
        return db.query(Equipment).count()

    @staticmethod
    def update_equipment(
        db: Session, equipment_id: int, equipment: EquipmentUpdate
    ) -> Equipment:
        """更新设备"""
        db_equipment = EquipmentService.get_equipment_by_id(db, equipment_id)

        # 如果修改序列号，检查是否已存在
        if equipment.serial_number and equipment.serial_number != db_equipment.serial_number:
            existing = db.query(Equipment).filter(
                Equipment.serial_number == equipment.serial_number
            ).first()
            if existing:
                raise BusinessExceptions("序列号已存在")

        update_data = equipment.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_equipment, field, value)

        db.add(db_equipment)
        db.commit()
        db.refresh(db_equipment)
        return db_equipment

    @staticmethod
    def delete_equipment(db: Session, equipment_id: int) -> dict:
        """删除设备"""
        db_equipment = EquipmentService.get_equipment_by_id(db, equipment_id)
        db.delete(db_equipment)
        db.commit()
        return {"message": "设备已删除"}

    @staticmethod
    def search_equipment(db: Session, keyword: str, skip: int = 0, limit: int = 10) -> list[Equipment]:
        """搜索设备"""
        query = db.query(Equipment)
        if keyword:
            query = query.filter(
                Equipment.name.like(f"%{keyword}%") |
                Equipment.model.like(f"%{keyword}%") |
                Equipment.serial_number.like(f"%{keyword}%")
            )
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_equipment_by_laboratory(db: Session, laboratory_id: int, skip: int = 0, limit: int = 10) -> list[Equipment]:
        """根据实验室ID获取设备列表"""
        return db.query(Equipment).filter(
            Equipment.laboratory_id == laboratory_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_equipment_count_by_laboratory(db: Session, laboratory_id: int) -> int:
        """根据实验室ID获取设备数量"""
        return db.query(Equipment).filter(Equipment.laboratory_id == laboratory_id).count()

    @staticmethod
    def get_equipment_by_maintenance_status(db: Session, status: str, skip: int = 0, limit: int = 10) -> list[Equipment]:
        """根据维护状态获取设备列表"""
        return db.query(Equipment).filter(
            Equipment.maintenance_status == status
        ).offset(skip).limit(limit).all()
