
from sqlalchemy import Column, Integer, String, BigInteger, text, Boolean
from app.db.base import Base


class TopicChat(Base):
    __tablename__ = "topic_chats"

    id = Column(String(255), primary_key=True, index=True, nullable=False)

    associated_topic_id = Column(String(255), unique=False, nullable=False)

    chat_message = Column(String, nullable=True)

    sent_by_user = Column(Boolean, nullable=False)

    # PostgreSQL-native millisecond timestamps
    created_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"))
