from pydantic import BaseModel
from datetime import datetime

#login request
class LoginRequest(BaseModel):
    email: str 
    password: str

#register request
class CreateUserRequest(BaseModel):
    email: str
    password: str
    username: str

#login response
class LoginResponse(BaseModel):
    message: str
    username: str
    email: str

#user response
#登録後やログイン後に返すユーザ情報
class UserResponse(BaseModel):
    email: str
    username: str
    created_at: datetime