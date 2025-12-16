from sqlalchemy.orm import Session
from models.user import User
from schemas.user import CreateUserRequest

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: CreateUserRequest):
    user = User(email=user.email, password=user.password, username=user.username, introduction=user.introduction)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
