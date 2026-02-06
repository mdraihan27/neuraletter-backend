from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
import time
from app.core.config import settings
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
def create_jwt_token(
    user_id: str,
    user_email: str

) -> str:
    now = int(time.time())
    secret_key :str = settings.JWT_SECRET_KEY
    issuer: str = "neuraletter-backend"
    audience: str = "neuraletter-frontend"
    algorithm: str = settings.JWT_ALGORITHM
    expires_in_seconds: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 3600

    payload = {
        "user_id": user_id,
        "user_email": user_email,
        "iat": now,
        "nbf": now,
        "exp": now + expires_in_seconds,
        "iss": issuer,
        "aud": audience,
    }

    token = jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm,
    )

    return token
def verify_jwt_token(
    token: str

) -> dict:
    try:

        secret_key = settings.JWT_SECRET_KEY
        issuer: str = "neuraletter-backend"
        audience: str = "neuraletter-frontend"
        algorithm: str = settings.JWT_ALGORITHM

        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
        )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = verify_jwt_token(token)
        user_id = payload["user_id"]
        user_email = payload["user_email"]

        if user_id is None or user_email is None:
            raise HTTPException(status_code=401, detail="Invalid token, try logging in again")

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
