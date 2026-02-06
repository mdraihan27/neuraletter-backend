from sqlalchemy import Column, Integer, String, BigInteger, text
from app.db.base import Base



class UserVerification(Base):
    __tablename__ = "user_verification_data"

    id = Column(String(255), primary_key=True, index=True)

    associated_user_id = Column(String(255), unique=True, nullable=False)

    verification_code = Column(Integer, nullable=False)


    expire_at = Column(BigInteger, nullable=False)

    generated_at = Column(BigInteger, nullable=False)

