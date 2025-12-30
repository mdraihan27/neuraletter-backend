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
from app.services.mistral.collect_update_service import combined_task
from app.services.mistral.conversation_service import MistralConversationService
from app.services.topic_service import TopicService

conversation_service = MistralConversationService()
router = APIRouter()

class ChatRequest(BaseModel):
    topic_id: str
    message: str

@router.post("/chat/")
def chat_with_ai(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db), chat_request: ChatRequest = None):
    try:
        return conversation_service.chat_with_ai(chat_request.message, chat_request.topic_id, current_user, db)
        # return conversation_service.create_agent()
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@router.post("/gen/")
def chat():
    try:
        return combined_task(
         "Update on Natural resources Policy of UN",)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



