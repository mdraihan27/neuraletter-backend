from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services import user_verification_service


router = APIRouter()

class Verification(BaseModel):
    verification_code: int

@router.post("/code")
def send_verification_code(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        print(current_user)
        return user_verification_service.send_verification_email(current_user["user_email"], current_user["user_id"], db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/verify")
def verify_verification_code(verification: Verification, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        print(current_user)
        return user_verification_service.verify_code(current_user["user_id"], verification.verification_code, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
