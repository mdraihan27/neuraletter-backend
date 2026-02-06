from fastapi import Depends
from starlette.responses import JSONResponse
from app.services.email_service import send_email
import random
from app.models.user_verification import UserVerification
from app.models.user import User
import time
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.utils.random_generator import generate_random_string



def send_verification_email(to_email: str, user_id_in_context: str, db: Session ) -> JSONResponse :

    try:
        code = random.randint(100000, 999999)

        user_verification = db.query(UserVerification).filter(UserVerification.associated_user_id == user_id_in_context).first()

        if user_verification is None:
            user_verification = UserVerification(
                id = generate_random_string(),
                associated_user_id=user_id_in_context,
                verification_code=code,
                expire_at=int(time.time() * 1000) + 5 * 60 * 1000,
                generated_at=int(time.time() * 1000)
            )
        else :
            user_verification.verification_code = str(code)
            user_verification.expire_at = int(time.time() * 1000) + 5 * 60 * 1000
            user_verification.generated_at = int(time.time() * 1000)

        subject = "Verify Your Neuraletter Account"
        body = f"Your verification code is: {code}. It will expire in 5 minutes."
        send_email(to_email, subject, body)
        db.add(user_verification)
        db.commit()
        db.refresh(user_verification)
        return JSONResponse(content={"message":"Verification email sent successfully"}, status_code=200)
    except Exception as e:
        db.rollback()
        print(f"Failed to send verification email: {e}")
        return JSONResponse(content={"message":"Failed to send verification email"}, status_code=500)


def verify_code(user_id_in_context: str, code: int, db: Session ) -> JSONResponse:

    try:
        user_verification = db.query(UserVerification).filter(UserVerification.associated_user_id == user_id_in_context).first()
        if user_verification is None:
            return JSONResponse(content={"message":"Verification data not found, try again"}, status_code=404)
        if user_verification.verification_code != code:
            return JSONResponse(content={"message":"Invalid code"}, status_code=404)
        if user_verification.expire_at < int(time.time() * 1000):
            return JSONResponse(content={"message":"Code has expired, please request a new one"}, status_code=404)

        user = db.query(User).filter(User.id == user_id_in_context).first()
        if user is None:
            return JSONResponse(content={"message":"User not found"}, status_code=404)

        if user.is_verified:
            return JSONResponse(content={"message":"User is already verified"}, status_code=409)

        user.is_verified = True
        user_verification.expire_at = int(time.time() * 1000)  
        db.commit()
        db.refresh(user)
        db.refresh(user_verification)

        return JSONResponse(content={"message":"Code verified successfully"}, status_code=200)
    except Exception as e:
        db.rollback()
        print(f"Failed to verify code: {e}")
        return JSONResponse(content={"message":"Internal server error"}, status_code=500)