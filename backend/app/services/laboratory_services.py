from sqlalchemy.orm import Session
from app.model.laboratory import Laboratory
from app.schemas.laboratory import LaboratoryCreate, LaboratoryUpdate
from app.common.exceptions import BusinessExceptions


class LaboratoryService:
    @staticmethod
    def create_laboratory(db: Session, laboratory: LaboratoryCreate) -> Laboratory:
        """创建实验室"""
        print('='*50)
        print('接收到的实验室数据:')
        print(f'  name: {laboratory.name} (type: {type(laboratory.name).__name__})')
        print(f'  description: {laboratory.description} (type: {type(laboratory.description).__name__})')
        print(f'  location: {laboratory.location} (type: {type(laboratory.location).__name__})')
        print(f'  capacity: {laboratory.capacity} (type: {type(laboratory.capacity).__name__})')
        print(f'  manager_id: {laboratory.manager_id} (type: {type(laboratory.manager_id).__name__})')
        print(f'  status: {laboratory.status} (type: {type(laboratory.status).__name__})')
        print('='*50)

        db_laboratory = Laboratory(
            name=laboratory.name,
            description=laboratory.description,
            location=laboratory.location,
            capacity=laboratory.capacity,
            manager_id=laboratory.manager_id,
            status=laboratory.status,
        )
        db.add(db_laboratory)
        db.commit()
        db.refresh(db_laboratory)
        return db_laboratory

    @staticmethod
    def get_laboratory_by_id(db: Session, laboratory_id: int) -> Laboratory:
        """根据ID获取实验室"""
        laboratory = db.query(Laboratory).filter(Laboratory.id == laboratory_id).first()
        if not laboratory:
            raise BusinessExceptions("实验室不存在")
        return laboratory

    @staticmethod
    def get_all_laboratories(db: Session, skip: int = 0, limit: int = 10) -> list[Laboratory]:
        """获取所有实验室列表"""
        return db.query(Laboratory).offset(skip).limit(limit).all()

    @staticmethod
    def get_laboratories_count(db: Session) -> int:
        """获取实验室总数"""
        return db.query(Laboratory).count()

    @staticmethod
    def update_laboratory(
        db: Session, laboratory_id: int, laboratory: LaboratoryUpdate
    ) -> Laboratory:
        """更新实验室"""
        db_laboratory = LaboratoryService.get_laboratory_by_id(db, laboratory_id)

        update_data = laboratory.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_laboratory, field, value)

        db.add(db_laboratory)
        db.commit()
        db.refresh(db_laboratory)
        return db_laboratory

    @staticmethod
    def delete_laboratory(db: Session, laboratory_id: int) -> dict:
        """删除实验室"""
        db_laboratory = LaboratoryService.get_laboratory_by_id(db, laboratory_id)
        db.delete(db_laboratory)
        db.commit()
        return {"message": "实验室已删除"}

    @staticmethod
    def search_laboratories(db: Session, keyword: str, skip: int = 0, limit: int = 10) -> list[Laboratory]:
        """搜索实验室"""
        query = db.query(Laboratory)
        if keyword:
            query = query.filter(
                Laboratory.name.like(f"%{keyword}%") |
                Laboratory.location.like(f"%{keyword}%")
            )
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_laboratories_by_manager(db: Session, manager_id: int, skip: int = 0, limit: int = 10) -> list[Laboratory]:
        """根据管理员ID获取实验室列表"""
        return db.query(Laboratory).filter(Laboratory.manager_id == manager_id).offset(skip).limit(limit).all()
