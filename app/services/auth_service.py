from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi.params import Depends
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.utils.user_util import create_user_response
from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from fastapi import status
from app.core.auth import create_jwt_token, verify_jwt_token
from app.utils.random_generator import generate_random_string
from fastapi.responses import RedirectResponse

try:
    import bcrypt as _bcrypt  # type: ignore
    _ = _bcrypt.__about__.__version__  # raises if missing on bcrypt>=4.1
    _BCRYPT_OK = True
except Exception:
    _BCRYPT_OK = False

_pwd_schemes = ["bcrypt", "pbkdf2_sha256"] if _BCRYPT_OK else ["pbkdf2_sha256"]
pwd_context = CryptContext(schemes=_pwd_schemes, deprecated="auto")



class AuthService:
    def __init__(self):
        pass

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)


    def create_user(self, user_data, db: Session) -> JSONResponse:

        try:

            if db.query(User).filter(User.email == user_data.email).first():
                raise Exception("User already exists")

            if len(user_data.password) < 8:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Password must be at least 8 characters long."}
                )
            hashed_password = self.hash_password(user_data.password)
            user = User(
                id=generate_random_string(),
                email=user_data.email,
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name
            )

            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt_token(user.id, user.email)
            user_response = create_user_response(user)


            return JSONResponse(content={"message":"User created successfully", "user_info":user_response, "access_token": token, "token_type": "bearer"}, status_code=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            db.rollback()
            if str(e) == "User already exists":
                return JSONResponse(content={"message":"User with this email already exists"}, status_code=status.HTTP_400_BAD_REQUEST)
            return JSONResponse(content={"message":"An unexpected error occurred"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def authenticate_user(self, email: str, password: str, db: Session) -> JSONResponse:

        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return JSONResponse(content={"message":"User does not exist", }, status_code=status.HTTP_404_NOT_FOUND)
            elif not self.verify_password(password, user.hashed_password):
                return JSONResponse(content={"message": "Wrong username or password"}, status_code=status.HTTP_401_UNAUTHORIZED)

            token = create_jwt_token(user.id, user.email)
            user_response = create_user_response(user)
            return JSONResponse(content={"message":"Successfully logged in","user_info":user_response, "access_token": token, "token_type": "bearer"}, status_code=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return JSONResponse(content={"message":"An unexpected error occurred"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



def handle_google_login(user_info: dict, db: Session) -> RedirectResponse | JSONResponse:
    try:
        user = db.query(User).filter(User.email == user_info["email"]).first()

        if not user:
            user = User(
                id=generate_random_string(),
                email=user_info["email"],
                first_name=user_info.get("given_name", ""),
                last_name=user_info.get("family_name", ""),
                is_verified=True,
                hashed_password= generate_random_string(32)
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_jwt_token(user.id, user.email)

        query = urlencode({
            "access_token": token
        })

        return RedirectResponse(
            url=f"{settings.CORS_ALLOWED_ORIGINS[0]}/login/google-callback?{query}",
            status_code=302,
        )

        # return JSONResponse(
        #     content={
        #         "message": "Login successful",
        #         "access_token": token,
        #         "token_type": "bearer"
        #     },
        #     status_code=200
        # )

    except Exception as e:
        db.rollback()
        return JSONResponse(
            content={"message": "Login with Google failed"},
            status_code=401
        )
