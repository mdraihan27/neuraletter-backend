
from sqlalchemy import Column, Integer, String, BigInteger, text, Boolean
from app.db.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(String(255), primary_key=True, index=True, nullable=False)

    associated_user_id = Column(String(255), nullable=False)

    title = Column(String(255), nullable=True)

    description = Column(String(1000), nullable=True)

    model = Column(String(255), nullable=False)

    tier = Column(String(255), nullable=False)

    due_payment = Column(Integer, nullable=False)

    update_frequency_hours = Column(Integer, nullable=False)

    next_update_time = Column(BigInteger, nullable=True)

    ai_conversation_id = Column(String(255), nullable=True)

    created_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"))

    updated_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"), onupdate=text("EXTRACT(EPOCH FROM NOW()) * 1000"))
