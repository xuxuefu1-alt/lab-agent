from pydantic import BaseModel, Field, model_validator


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")
    confirm_password: str = Field(..., min_length=6, max_length=50, description="确认密码")

    def validate_passwords(self):
        """验证两次密码是否一致"""
        if self.new_password != self.confirm_password:
            raise ValueError("新密码和确认密码不一致")
        if self.old_password == self.new_password:
            raise ValueError("新密码不能与旧密码相同")
        return True


    @model_validator(mode="after")
    def validate_passwords_model(self):
        self.validate_passwords()
        return self


class ChangePasswordResponse(BaseModel):
    message: str = "密码修改成功"
