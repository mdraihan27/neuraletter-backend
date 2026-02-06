import json
import random
import time

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from app.utils.encryption import encrypt_data , decrypt_data
from starlette.responses import JSONResponse
from cryptography.fernet import Fernet
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib

from app.core.auth import get_current_user, create_jwt_token
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.user_verification import UserVerification
from app.services.email_service import send_email
from app.utils.random_generator import generate_random_string
from app.utils.user_util import create_user_response

try:
    import bcrypt as _bcrypt  
    _ = _bcrypt.__about__.__version__  
    _BCRYPT_OK = True
except Exception:
    _BCRYPT_OK = False


_pwd_schemes = ["bcrypt", "pbkdf2_sha256"] if _BCRYPT_OK else ["pbkdf2_sha256"]
pwd_context = CryptContext(schemes=_pwd_schemes, deprecated="auto")


def hash_password( password: str) -> str:
    return pwd_context.hash(password)

# def reset_password_with_access_token(new_password: str, old_password: str, current_user: dict, db: Session) -> JSONResponse:
#     try:
#         if len(new_password) < 8:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={"message": "Password must be at least 8 characters long."}
#             )
#
#         user = db.query(User).filter(User.id == current_user["user_id"]).first()
#         if not user:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={"message": "User not found."}
#             )
#
#         # Verify old password
#         if not pwd_context.verify(old_password, user.hashed_password):
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={"message": "Previous password is incorrect."}
#             )
#
#         # Hash new password and update
#         new_hashed_password = hash_password(new_password)
#         user.hashed_password = new_hashed_password
#
#         db.add(user)
#         db.commit()
#         db.refresh(user)
#
#         return JSONResponse(
#             content={"success": "true", "message": "Password reset successfully."},
#             status_code=200
#         )
#
#     except Exception as e:
#         db.rollback()
#         return JSONResponse(
#             content={"success": "false", "message": str(e)},
#             status_code=500
#         )

def reset_password_with_reset_code(new_password: str, reset_password_code:str, current_user:dict, db: Session) ->JSONResponse:
    try:

        if len(new_password) < 8:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success":"false", "message": "Password must be at least 8 characters long."}
            )

        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found."}
            )

        user_verification = db.query(UserVerification).filter(UserVerification.associated_user_id == user.id).first()
        if user_verification is None:
            return JSONResponse(content={"message":"Verification data not found, try again"}, status_code=404)

        if str(user_verification.verification_code) != str(reset_password_code):
            return JSONResponse(content={"message":"Invalid reset password code"}, status_code=400)

        if user_verification.expire_at < int(time.time() * 1000):
            return JSONResponse(content={"message":"Reset password code has expired, please request a new one"}, status_code=400)

        user_verification.expire_at = int(time.time() * 1000)
        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.add(user_verification)
        db.commit()
        db.refresh(user)

        return JSONResponse(content={"message" : "Password reset successfully"}, status_code=200)


    except Exception as e:
        db.rollback()
        return JSONResponse(content={"message" : e.__str__()}, status_code=500)




def send_password_reset_email(user_email:str, db:Session) ->JSONResponse:
    try:
        code = random.randint(100000, 999999)

        user = db.query(User).filter(User.email == user_email).first()

        if user is None:
            return JSONResponse(content={"message":"User not found"}, status_code=404)

        user_verification = db.query(UserVerification).filter(
            UserVerification.associated_user_id == user.id).first()

        if user_verification is None:
            user_verification = UserVerification(
                id=generate_random_string(),
                associated_user_id=user.id,
                verification_code=code,
                expire_at=int(time.time() * 1000) + 5 * 60 * 1000,
                generated_at=int(time.time() * 1000)
            )
        else:
            user_verification.verification_code = str(code)
            user_verification.expire_at = int(time.time() * 1000) + 5 * 60 * 1000
            user_verification.generated_at = int(time.time() * 1000)


        subject = "Password reset request"
        body = f"Your password reset code is: {code}. It will expire in 5 minutes."
        send_email(user_email, subject, body)
        db.add(user_verification)
        db.commit()
        db.refresh(user_verification)
        return JSONResponse(content={"message": "Password reset email sent successfully"}, status_code=200)
    except Exception as e:
        db.rollback()
        print(f"Failed to send verification email: {e}")
        return JSONResponse(content={"message": "Failed to send verification email"}, status_code=500)



def verify_reset_password_code(user_email: str, code: int, db: Session) -> JSONResponse:

    try:
        user = db.query(User).filter(User.email == user_email).first()
        if user is None:
            return JSONResponse(content={"message":"User not found"}, status_code=404)


        user_verification = db.query(UserVerification).filter(UserVerification.associated_user_id == user.id).first()
        if user_verification is None:
            return JSONResponse(content={"message":"Verification data not found, try again"}, status_code=404)
        if user_verification.verification_code != code:
            return JSONResponse(content={"message":"Invalid code"}, status_code=404)
        if user_verification.expire_at < int(time.time() * 1000):
            return JSONResponse(content={"message":"Code has expired, please request a new one"}, status_code=404)

        token = create_jwt_token(user.id, user.email)

        reset_password_code = random.randint(100000, 999999)
        user_verification.verification_code = reset_password_code
        user_verification.expire_at = int(time.time() * 1000) + 5*60*1000  
        db.commit()
        db.refresh(user)
        db.refresh(user_verification)

        return JSONResponse(
            content={"message": "Code verified successfully", "access_token": token, "reset_password_code":reset_password_code, "user_info": create_user_response(user), "token_type": "bearer"},
            status_code=200)

    except Exception as e:
        db.rollback()
        print(f"Failed to verify code: {e}")
        return JSONResponse(content={"message":"Internal server error"}, status_code=500)




def create_reset_password_token(user_id: str, user_email: str) -> str:
    data = json.dumps({
        "id": user_id,
        "email": user_email,
        "expire_at": int(time.time() * 1000) + 5 * 60 * 1000
    })
    return encrypt_data(data)


def decrypt_reset_password_token(token: str):
    decrypted = decrypt_data(token)
    if decrypted is None:
        return None
    return json.loads(decrypted)
