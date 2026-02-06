
from sqlalchemy import Column, Integer, String, BigInteger, text, Boolean
from app.db.base import Base


class Update(Base):
    __tablename__ = "updates"

    id = Column(String(255), primary_key=True, index=True, nullable=False)

    associated_topic_id = Column(String(255), nullable=False)

    title = Column(String(255), nullable=True)

    batch_id=Column(String(255), nullable=False)

    author = Column(String(1000), nullable=True)

    summary = Column(String, nullable=True)

    source_url = Column(String, nullable=True)

    date = Column(BigInteger, nullable=True)

    key_points = Column(String, nullable=True)

    image_link = Column(String(255), nullable=True)

    created_at = Column(BigInteger, nullable=False, server_default=text("EXTRACT(EPOCH FROM NOW()) * 1000"))

