import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.endpoints import auth, health, user_verification, user, google_auth, reset_password, topic, topic_chat, update
from app.api.v1.endpoints.ai import ai_endpoints
from app.core.config import settings
from app.db.init_db import init_db
from app.api.v1.endpoints.google_auth import router as google_auth_router
from app.services.task_schedule.schedule_update_collection_service import start_topic_update_scheduler

# from app.services.mistral.conversation_service import continue_conversation, start_conversation, create_agent

app = FastAPI(title="Neuraletter API")

# authenticated user has attribute user_id instead of id
# ✅ CORS MUST BE HERE — ON THE REAL APP
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    same_site="lax",
    https_only=False,
)
# Create database tables if they don't exist
init_db()

print("CORS", settings.CORS_ALLOWED_ORIGINS)

# ✅ Routers AFTER middleware
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(user_verification.router, prefix="/api/v1/user/verification", tags=["User Verification"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(google_auth.router, prefix="/api/v1/auth", tags=["Google Auth"])
app.include_router(reset_password.router, prefix="/api/v1/user", tags=["Reset Password"])
app.include_router(google_auth_router, prefix="/api/v1")
app.include_router(topic.router, prefix="/api/v1/topic", tags=["Topic"])
app.include_router(update.router, prefix="/api/v1/update", tags=["Update"])
app.include_router(ai_endpoints.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(topic_chat.router, prefix="/api/v1/topic/chat", tags=["Chat Topic"])


# @app.on_event("startup")
# def _start_schedulers() -> None:
#     start_topic_update_scheduler()


# //ai test run

# message = input("Message: ")
# print(start_conversation(message))
# conversation_id = input("Conversation ID: ")
# while(True):
#
#     message = input("Message: ")
#     print(continue_conversation(conversation_id, message))
#

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # combined_task(
    #     "Update of Dhaka, Bangladesh weather of upcoming 10 days including temperature, humidity, wind speed and chance of rain.")


