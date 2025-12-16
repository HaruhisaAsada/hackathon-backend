from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.user import LoginRequest, LoginResponse, CreateUserRequest, UserResponse
from cruds.user import create_user, get_user_by_email
from db import get_db

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, login_data.email)
    if not user or not user.password == login_data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(message="Login successful", username=user.username, email=user.email, introduction=user.introduction)

@router.post("/register", response_model=UserResponse)
async def register(register_data: CreateUserRequest, db: Session = Depends(get_db)):

    existing_user = get_user_by_email(db, register_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user = create_user(db, register_data)
    return UserResponse(
        email=user.email,
        username=user.username,
        introduction=user.introduction,
        created_at=user.created_at
    )