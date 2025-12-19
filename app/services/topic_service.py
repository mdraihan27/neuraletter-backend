from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.models.topic import Topic
from app.utils.random_generator import generate_random_string


class TopicService:

    def create_new_topic(self, title: str, tier:str, model:str, authenticated_user_id:str, db: Session) -> JSONResponse:
        try:
            if tier == "free":
                if model != "mistral-large-2512":
                    return JSONResponse(
                        content={"message": "Invalid model for free tier"},
                        status_code=400
                    )
            elif tier == "premium":
                if model != "mistral-large-2512":
                    return JSONResponse(
                        content={"message": "Invalid model for free tier"},
                        status_code=400
                    )
            elif tier== "pay_as_you_go":
                if model != "mistral-large-2512":
                    return JSONResponse(
                        content={"message": "Invalid model for free tier"},
                        status_code=400
                    )
            else:
                return JSONResponse(
                    content={"message": "Invalid tier specified"},
                    status_code=400
                )

# there is reason behind structuring the code like this, that is to allow easy expansion in future when more models are added for different tiers


            new_topic = Topic(
                id=generate_random_string(32),
                title=title,
                tier=tier,
                model=model,
                associated_user_id=authenticated_user_id,
                description = None,
                due_payment=0,

            )
            db.add(new_topic)
            db.commit()
            db.refresh(new_topic)

            return JSONResponse(
                content={
                    "message": "Topic created successfully",
                    "topic": {
                        "id": new_topic.id,
                        "title": new_topic.title,
                        "created_at": new_topic.created_at,
                        "tier": new_topic.tier,
                        "model": new_topic.model,
                        "due_payment": new_topic.due_payment
                    }
                },
                status_code=201
            )
        except Exception as e:
            db.rollback()
            print(f"Failed to create topic: {e}")
            return JSONResponse(
                content={"message": "Failed to create topic"},
                status_code=500
            )

    def get_topics_for_user(self, authenticated_user_id:str, db: Session) -> JSONResponse:
        try:
            topics = db.query(Topic).filter(Topic.associated_user_id == authenticated_user_id).all()
            topics_list = []
            for topic in topics:
                topics_list.append(
                    {
                        "id": topic.id,
                        "title": topic.title,
                    }
                )

            return JSONResponse(
                content={
                    "message": "Topics fetched successfully",
                    "topics": topics_list
                },
                status_code=200
            )
        except Exception as e:
            print(f"Failed to fetch topics: {e}")
            return JSONResponse(
                content={"message": "Failed to fetch topics"},
                status_code=500
            )

    def get_topic_by_id(self, topic_id:str, authenticated_user_id:str, db: Session) -> JSONResponse:
        try:
            topic = db.query(Topic).filter(Topic.id == topic_id, Topic.associated_user_id == authenticated_user_id).first()
            if not topic:
                return JSONResponse(
                    content={"message": "Topic not found"},
                    status_code=404
                )

            topic_data = {
                "id": topic.id,
                "title": topic.title,
                "created_at": topic.created_at,
                "tier": topic.tier,
                "model": topic.model,
                "description": topic.description,
                "due_payment": topic.due_payment
            }

            return JSONResponse(
                content={
                    "message": "Topic fetched successfully",
                    "topic_info": topic_data
                },
                status_code=200
            )
        except Exception as e:
            print(f"Failed to fetch topic: {e}")
            return JSONResponse(
                content={"message": "Failed to fetch topic"},
                status_code=500
            )


    def delete_topic_by_id(self, topic_id:str, authenticated_user_id:str, db: Session) -> JSONResponse:
        try:
            topic = db.query(Topic).filter(Topic.id == topic_id, Topic.associated_user_id == authenticated_user_id).first()
            if not topic:
                return JSONResponse(
                    content={"message": "Topic not found"},
                    status_code=404
                )

            db.delete(topic)
            db.commit()

            return JSONResponse(
                content={"message": "Topic deleted successfully"},
                status_code=200
            )
        except Exception as e:
            db.rollback()
            print(f"Failed to delete topic: {e}")
            return JSONResponse(
                content={"message": "Failed to delete topic"},
                status_code=500
            )


    def update_topic_by_id(self, topic_id:str, topic_update:dict, authenticated_user_id:str, db: Session) -> JSONResponse:
        try:
            topic = db.query(Topic).filter(Topic.id == topic_id, Topic.associated_user_id == authenticated_user_id).first()
            if not topic:
                return JSONResponse(
                    content={"message": "Topic not found"},
                    status_code=404
                )

            if topic_update.get("title") is not None and topic_update.get("title") !="":
                topic.title = topic_update["title"]

            if topic_update.get("tier") is not None and topic_update.get("tier") !="":
                if topic_update.get("tier")=="free":
                    topic.tier = "free"

                elif topic_update.get("tier")=="premium":
                    topic.tier = "premium"

                elif topic_update.get("tier")=="pay_as_you_go":
                    topic.tier = "pay_as_you_go"

                else:
                    return JSONResponse(
                        content={"message": "Invalid tier specified"},
                        status_code=400
                    )

            if topic_update.get("model") is not None and topic_update.get("model") !="":
                if topic.tier == "free":
                    if topic_update.get("model") == "ai-large-2512":
                        topic.model = "ai-large-2512"
                    else:
                        return JSONResponse(
                            content={"message": "Invalid model for free tier"},
                            status_code=400
                        )
                elif topic.tier == "premium":
                    if topic_update.get("model") == "ai-large-2512":
                        topic.model = "ai-large-2512"
                    else:
                        return JSONResponse(
                            content={"message": "Invalid model for premium tier"},
                            status_code=400
                        )
                elif topic.tier == "pay-as-you-go":
                    if topic_update.get("model") == "ai-large-2512":
                        topic.model = "ai-large-2512"
                    else:
                        return JSONResponse(
                            content={"message": "Invalid model for Pay As You Go tier"},
                            status_code=400
                        )


            db.add(topic)
            db.commit()
            db.refresh(topic)

            return JSONResponse(
                content={
                    "message": "Topic updated successfully",
                    "topic": {
                        "id": topic.id,
                        "title": topic.title,
                        "description": topic.description,
                        "created_at": topic.created_at,
                        "tier": topic.tier,
                        "model": topic.model,
                        "due_payment": topic.due_payment
                    }
                },
                status_code=200
            )
        except Exception as e:
            db.rollback()
            print(f"Failed to update topic: {e}")
            return JSONResponse(
                content={"message": "Failed to update topic"},
                status_code=500
            )