
from sqlalchemy import Column, Integer, String, BigInteger, text, Boolean
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(255), primary_key=True, index=True, nullable=False)

    email = Column(String(255), unique=True, index=True, nullable=False)

    is_verified = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")

    hashed_password = Column(String(255), nullable=False)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))

    created_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"))

    updated_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"), onupdate=text("EXTRACT(EPOCH FROM NOW()) * 1000"))
