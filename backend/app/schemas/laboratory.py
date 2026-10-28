from pydantic import BaseModel, ConfigDict, Field, field_validator


class LaboratoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="实验室名称")
    description: str | None = Field(default=None, max_length=1000, description="实验室描述")
    location: str = Field(..., min_length=1, max_length=255, description="实验室位置")
    capacity: int = Field(default=0, ge=0, description="实验室容纳人数")
    manager_id: int = Field(..., description="管理员ID")
    status: int = Field(default=1, description="状态 1正常 0禁用")

    @field_validator('description', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """将空字符串转换为None"""
        if v == '':
            return None
        return v


class LaboratoryCreate(LaboratoryBase):
    pass


class LaboratoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="实验室名称")
    description: str | None = Field(None, max_length=1000, description="实验室描述")
    location: str | None = Field(None, min_length=1, max_length=255, description="实验室位置")
    capacity: int | None = Field(None, ge=0, description="实验室容纳人数")
    manager_id: int | None = Field(None, description="管理员ID")
    status: int | None = Field(None, description="状态 1正常 0禁用")


class LaboratoryResponse(LaboratoryBase):
    id: int
    create_time: str | None = None
    update_time: str | None = None
    model_config = ConfigDict(from_attributes=True)
