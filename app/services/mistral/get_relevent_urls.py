from app.services.mistral.conversation_service import MistralConversationService

conversation_service = MistralConversationService()



def get_relevant_urls(topic_desc: str, content_json: str):
    base_prompt = (
        "You are a relevance filter for link extraction. Given a topic and a JSON array of sections (fields 'text' and 'url'), "
        "return only the URLs whose associated text aligns with the topic.\n"
        "Rules:\n"
        "1) Judge relevance using anchor text and its surrounding section text; ignore nav/ads/footer/legal content.\n"
        "2) Output exactly a Python list literal of URL strings; no explanations or extra text.\n"
        "3) Use only URLs from the provided JSON; deduplicate; prefer https; preserve first-seen order.\n"
        "4) If nothing matches, return an empty list [].\n"
        f"Topic: {topic_desc}\n"
        f"JSON: {content_json}\n"
    )

    result = conversation_service.request_ai(base_prompt)
    return result