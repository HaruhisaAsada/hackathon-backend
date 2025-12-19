from pydantic import BaseModel
from datetime import datetime

class LoginRequest(BaseModel):
    email: str 
    password: str

#register request
class CreateUserRequest(BaseModel):
    email: str
    password: str
    username: str
    introduction: str | None = None

#login response
class LoginResponse(BaseModel):
    message: str
    username: str
    email: str
    introduction: str | None = None

#user response
#登録後やログイン後に返すユーザ情報
class UserResponse(BaseModel):
    email: str
    username: str
    created_at: datetime
    introduction: str | None = None

class RecPidsResponse(BaseModel):
    rec_pids: list[str] | None = None
    rec_updated_at: datetime | None = None
