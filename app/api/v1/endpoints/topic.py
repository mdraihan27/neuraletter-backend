from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from app.core.auth import get_current_verified_user
from app.db.session import get_db
from app.services import user_service
from app.models.topic import Topic
from app.services.topic_service import TopicService

topic_service = TopicService()

router = APIRouter()

class CreateTopicRequest(BaseModel):
    title :str
    tier :str
    model :str
    update_frequency_hours: int

class GetTopicByIdRequest(BaseModel):
    topic_id : str

class TopicUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    tier: Optional[str] = None
    update_frequency_hours: Optional[int] = None

@router.post("/")
def create_topic(current_user: dict = Depends(get_current_verified_user), db: Session = Depends(get_db), create_topic_request: CreateTopicRequest = None):
    try:
        return topic_service.create_new_topic(
            create_topic_request.title,
            create_topic_request.tier,
            create_topic_request.model,
            create_topic_request.update_frequency_hours,
            current_user["user_id"],
            db,
        )
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@router.get("/user")
def get_all_topics_by_user(current_user: dict = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    try:
        return topic_service.get_topics_for_user(current_user["user_id"], db)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{topic_id}")
def get_topic_by_id(topic_id:str, current_user:dict = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    try:
        return topic_service.get_topic_by_id(topic_id, current_user["user_id"], db)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{topic_id}")
def delete_topic_by_id(topic_id:str, current_user:dict = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    try:
        return topic_service.delete_topic_by_id(topic_id, current_user["user_id"], db)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.patch("/{topic_id}")
def update_topic_by_id(topic_id:str, topic_update:TopicUpdate, current_user:dict = Depends(get_current_verified_user), db: Session = Depends(get_db)):
    try:
        return topic_service.update_topic_by_id(topic_id, topic_update.__dict__, current_user["user_id"], db)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
