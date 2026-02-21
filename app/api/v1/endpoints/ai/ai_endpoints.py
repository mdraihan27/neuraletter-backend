from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from app.core.auth import get_current_verified_user
from app.core.config import settings
from app.db.session import get_db
from app.services import user_service
from app.models.topic import Topic
from app.models.user import User
from app.services.mistral.conversation_service import MistralConversationService
from app.services.topic_service import TopicService
from app.services.task_schedule.schedule_update_collection_service import schedule_topic_update_at

conversation_service = MistralConversationService()
router = APIRouter()

class ChatRequest(BaseModel):
    topic_id: str
    message: str

class CollectUpdatesRequest(BaseModel):
    topic_id: str

@router.post("/chat/")
def chat_with_ai(current_user: dict = Depends(get_current_verified_user), db: Session = Depends(get_db), chat_request: ChatRequest = None):
    try:
        return conversation_service.chat_with_ai(chat_request.message, chat_request.topic_id, current_user, db)
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@router.post("/gen-agent/")
def generate_agent(
    current_user: dict = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):

    try:
        admin_email = (settings.ADMIN_EMAIL or "").strip().lower()
        if not admin_email:
            return JSONResponse(
                content={"message": "ADMIN_EMAIL is not configured"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user_email = str(current_user.get("user_email") or "").strip().lower()
        if user_email != admin_email:
            return JSONResponse(
                content={"message": "Only admin can access this endpoint"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            return JSONResponse(
                content={"message": "Only admin can access this endpoint"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_verified:
            return JSONResponse(
                content={"message": "User must be verified"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        
        main_agent = conversation_service.create_agent("mistral-large-2512")

        conversation_service.create_serp_topic_agent("mistral-large-2512", db)

        return main_agent
    except Exception as e:
        return JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/collect-updates/")
def collect_updates(
    collect_request: CollectUpdatesRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):

    try:
        topic = db.query(Topic).filter(
            Topic.id == collect_request.topic_id,
            Topic.associated_user_id == current_user["user_id"]
        ).first()
        
        if not topic:
            return JSONResponse(
                content={"message": "Topic not found or unauthorized"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if not topic.description:
            return JSONResponse(
                content={"message": "Topic description is required for content collection"},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        def run_collection():
            from app.db.session import SessionLocal
            from datetime import datetime
            bg_db = SessionLocal()
            try:
                bg_topic = bg_db.query(Topic).filter(Topic.id == topic.id).first()
                if bg_topic:
                    print(f"\nStarting content collection for topic: {bg_topic.description}")
                    result = conversation_service.run_serp_topic_enrichment(bg_topic, bg_db)

                    try:
                        freq = getattr(bg_topic, "update_frequency_hours", None) or 24
                        now_ms = int(datetime.utcnow().timestamp() * 1000)
                        bg_topic.next_update_time = now_ms + int(freq) * 60 * 60 * 1000
                        bg_db.add(bg_topic)
                        bg_db.commit()
                        schedule_topic_update_at(bg_topic.id, int(bg_topic.next_update_time))
                    except Exception as sched_err:
                        print(f"Failed to persist/schedule next update time: {sched_err}")

                    if isinstance(result, dict):
                        print(f"\n📊 Collection result: {result.get('status')}")
                        print(f"   Updates created: {len(result.get('updates_created', []))}")
                        if result.get('errors'):
                            print(f"   Errors: {result['errors']}")
                    else:
                        print("\n📊 Collection finished (no structured result returned)")
            except Exception as e:
                print(f"Background collection error: {e}")
            finally:
                bg_db.close()
        
        background_tasks.add_task(run_collection)
        
        return JSONResponse(
            content={
                "message": "Content collection started",
                "status": "processing",
                "topic_id": topic.id,
                "topic_description": topic.description,
                "note": "This process takes 2-5 minutes. Check updates endpoint for results."
            },
            status_code=status.HTTP_202_ACCEPTED
        )
        
    except Exception as e:
        return JSONResponse(
            content={"message": f"Error starting collection: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


