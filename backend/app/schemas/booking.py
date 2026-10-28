from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingBase(BaseModel):
    laboratory_id: int = Field(..., description="实验室ID")
    equipment_ids: list[int] = Field(default_factory=list, max_length=20, description="预约设备ID列表")
    start_time: str = Field(..., description="开始时间 (YYYY-MM-DD HH:mm)")
    end_time: str = Field(..., description="结束时间 (YYYY-MM-DD HH:mm)")
    purpose: str = Field(..., min_length=1, max_length=500, description="预约目的")
    student_count: int = Field(default=1, ge=1, description="学生数量")
    remarks: str | None = Field(None, max_length=500, description="备注")


class BookingCreate(BookingBase):
    pass


class BookingApprove(BaseModel):
    status: str = Field(..., description="审批状态")
    reject_reason: str | None = Field(None, max_length=500, description="拒绝原因")
    remarks: str | None = Field(None, max_length=500, description="备注")


class BookingUpdate(BaseModel):
    laboratory_id: int | None = Field(None, description="实验室ID")
    start_time: str | None = Field(None, description="开始时间 (YYYY-MM-DD HH:mm)")
    end_time: str | None = Field(None, description="结束时间 (YYYY-MM-DD HH:mm)")
    purpose: str | None = Field(None, min_length=1, max_length=500, description="预约目的")
    student_count: int | None = Field(None, ge=1, description="学生数量")
    remarks: str | None = Field(None, max_length=500, description="备注")
    equipment_ids: list[int] | None = Field(None, max_length=20, description="预约设备ID列表")


class BookingResponse(BookingBase):
    id: int
    user_id: int
    status: str
    reject_reason: str | None = None
    approved_by: int | None = None
    approved_time: datetime | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None
    model_config = ConfigDict(from_attributes=True)
