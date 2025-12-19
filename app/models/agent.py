
from sqlalchemy import Column, Integer, String, BigInteger, text, Boolean
from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(255), primary_key=True, index=True, nullable=False)

    agent_id = Column(String(255),  nullable=False)

    model = Column(String(255), unique=True, nullable=False)

    # PostgreSQL-native millisecond timestamps
    created_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"))

