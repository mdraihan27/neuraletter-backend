from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup", response_model=TokenResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return auth_service.create_user(user, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    try:
        return auth_service.authenticate_user(credentials.email, credentials.password, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
