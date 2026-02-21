from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
import time
from app.core.config import settings
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from urllib.parse import quote
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


def get_current_verified_user(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token, try logging in again")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_verified:
        frontend_base = (settings.FRONTEND_BASE_URL or "").rstrip("/")
        email = user.email or current_user.get("user_email") or ""
        redirect_url = f"{frontend_base}/verification?email={quote(email)}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "User needs to be verified",
                "redirect_url": redirect_url,
            },
        )

    return current_user
