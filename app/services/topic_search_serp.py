from sqlalchemy.orm import Session
from app.models.topic import Topic
from app.services.serpapi.search_serp import search_serp_with_topic_description

def search_topic_serp_by_id(topic_id: str, db: Session):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        print("Topic not found")
        return
    description = topic.description
    if not description:
        print("No description found for topic.")
        return
    search_serp_with_topic_description(description)
