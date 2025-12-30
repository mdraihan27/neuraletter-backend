from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.models.topic import Topic
from app.models.topic_chat import TopicChat


class TopicChatService:
    def get_topic_chat(self, topic_id:str, current_user: dict, db: Session):
       try:
           topic = db.query(Topic).filter(Topic.id == topic_id,
                                          Topic.associated_user_id == current_user["user_id"]).first()

           if not topic:

               raise Exception("Topics not found")

           topic_chats = db.query(TopicChat).filter(TopicChat.associated_topic_id == topic_id).all()

           topic_chat_jsons = []

           for topic_chat in topic_chats:
                topic_chat_jsons.append({
                    "id": topic_chat.id,
                    "associated_topic_id": topic_chat.associated_topic_id,
                    "chat_message": topic_chat.chat_message,
                    "sent_by_user": topic_chat.sent_by_user,
                    "created_at": topic_chat.created_at
                })


           return JSONResponse({"message": "Topic chats fetched successfully", "topic_chats": topic_chat_jsons}, status_code=200)

       except Exception as e:
            print(f"Failed to fetch topic chats: {e}")
            return JSONResponse(
            content={"message": e},
            status_code=500
            )