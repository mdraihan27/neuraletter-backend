from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services import user_service
from app.models.topic import Topic
from app.services.mistral.collect_update_service import collect_updates_for_topic
from app.services.mistral.conversation_service import MistralConversationService
from app.services.topic_service import TopicService

conversation_service = MistralConversationService()
router = APIRouter()

class ChatRequest(BaseModel):
    topic_id: str
    message: str

class CollectUpdatesRequest(BaseModel):
    topic_id: str

@router.post("/chat/")
def chat_with_ai(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db), chat_request: ChatRequest = None):
    try:
        return conversation_service.chat_with_ai(chat_request.message, chat_request.topic_id, current_user, db)
        # return conversation_service.create_agent()
    except Exception as e:
        JSONResponse(
            content={"message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)



@router.post("/gen-agent/")
def generate_agent(db: Session = Depends(get_db)):
    """(Re)generate agents used by the system.

    - Creates the main conversation/description agent (existing behavior).
    - Also creates/updates the SERP topic-details agent and stores its id
      in the Agent row with id `ePscUwZlIHIdsfsgerseg235vdaYTVMM`.
    """
    try:
        # Existing conversation agent (returned as before)
        main_agent = conversation_service.create_agent("mistral-large-2512")

        # New SERP topic-details agent, stored under the fixed Agent.id
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger content collection pipeline for a topic.
    This runs as a background task since it takes 2-5 minutes.
    
    Request body:
        topic_id: The ID of the topic to collect updates for
        
    Returns:
        Immediate response indicating pipeline has started
    """
    try:
        # Verify topic exists and belongs to user
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
        
        # Create a new database session for the background task
        def run_collection():
            from app.db.session import SessionLocal
            bg_db = SessionLocal()
            try:
                # Refresh topic in new session
                bg_topic = bg_db.query(Topic).filter(Topic.id == topic.id).first()
                if bg_topic:
                    print(f"\n🚀 Starting content collection for topic: {bg_topic.description}")
                    result = collect_updates_for_topic(bg_topic, bg_db)
                    print(f"\n📊 Collection result: {result['status']}")
                    print(f"   Updates created: {len(result.get('updates_created', []))}")
                    if result.get('errors'):
                        print(f"   Errors: {result['errors']}")
            except Exception as e:
                print(f"Background collection error: {e}")
            finally:
                bg_db.close()
        
        # Add to background tasks
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


