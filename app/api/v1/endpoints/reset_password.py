from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.auth import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.services.reset_password_service import send_password_reset_email, \
    verify_reset_password_code, reset_password_with_reset_code

router = APIRouter()

class PasswordResetRequest(BaseModel):
    reset_password_code: int
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class Verification(BaseModel):
    email: str
    verification_code: int

@router.patch("/password/reset")
def reset_password_using_token(password_reset_request:PasswordResetRequest, current_user:dict = Depends(get_current_user), db: Session = Depends(get_db)) ->JSONResponse:
    try:
       return reset_password_with_reset_code(password_reset_request.new_password, password_reset_request.reset_password_code, current_user, db)


    except Exception as e:
        return JSONResponse(content={"message" : "Password reset unsuccessful"}, status_code=500)



@router.post("/password/forget/code")
def send_forgot_password_email(forgot_password_request:ForgotPasswordRequest, db: Session = Depends(get_db)) ->JSONResponse:
    try:
        return send_password_reset_email(forgot_password_request.email, db)


    except Exception as e:
        return JSONResponse(content={"message" : "Password reset unsuccessful"}, status_code=500)

@router.post("/password/forget/verify")
def verify_verification_code(verification: Verification, db: Session = Depends(get_db)):
    try:

        return verify_reset_password_code(verification.email, verification.verification_code, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
