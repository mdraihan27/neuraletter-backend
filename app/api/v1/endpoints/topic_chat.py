from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services import user_service
from app.models.topic import Topic
from app.services.topic_chat_service import TopicChatService

topic_chat_service = TopicChatService()

router = APIRouter()

class GetTopicChatRequest(BaseModel):
    topic_id: str


@router.get("/{topic_id}")
def get_topic_chat_by_topic_id(topic_id:str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return topic_chat_service.get_topic_chat(topic_id, current_user, db)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)




