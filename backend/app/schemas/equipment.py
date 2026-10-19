from pydantic import BaseModel, ConfigDict, Field


class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="设备名称")
    equipment_type: str = Field(..., min_length=1, max_length=50, description="设备类型")
    laboratory_id: int = Field(..., description="所属实验室ID")
    model: str | None = Field(None, max_length=100, description="设备型号")
    serial_number: str | None = Field(None, max_length=100, description="序列号")
    description: str | None = Field(None, max_length=1000, description="设备描述")
    purchase_date: str | None = Field(None, description="购入日期 YYYY-MM-DD")
    maintenance_status: str = Field(default="正常", description="维护状态 正常/维修中/停用")
    status: int = Field(default=1, description="状态 1正常 0禁用")


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="设备名称")
    equipment_type: str | None = Field(None, min_length=1, max_length=50, description="设备类型")
    laboratory_id: int | None = Field(None, description="所属实验室ID")
    model: str | None = Field(None, max_length=100, description="设备型号")
    serial_number: str | None = Field(None, max_length=100, description="序列号")
    description: str | None = Field(None, max_length=1000, description="设备描述")
    purchase_date: str | None = Field(None, description="购入日期 YYYY-MM-DD")
    maintenance_status: str | None = Field(None, description="维护状态 正常/维修中/停用")
    status: int | None = Field(None, description="状态 1正常 0禁用")


class EquipmentResponse(EquipmentBase):
    id: int
    create_time: str | None = None
    update_time: str | None = None
    model_config = ConfigDict(from_attributes=True)
