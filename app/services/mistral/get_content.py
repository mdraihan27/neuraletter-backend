from app.services.mistral.conversation_service import MistralConversationService

conversation_service = MistralConversationService()



def get_content_json(topic_desc: str, content_json: str):
    base_prompt = (
        "You are an article summarization assistant. analyze the provided JSON and return ONLY a JSON object (no prose, no code blocks).\n"
        "Expected output shape: {\"title\": string|null, \"author\": string|null, \"summary\": string, \"key_points\": [string], \"lead_image\": string|null}.\n"
        "I will also provide a topic, you will need to analyze the json based on that topic. What I mean is, the summary you are providing must align with the topic\n"
        "Requirements:\n"
        "1) Keep summary concise but comprehensive (3-6 sentences).\n"
        "2) key_points should be 3-7 short bullet-like strings covering the main takeaways.\n"
        "3) lead_image: if the JSON includes an image URL near the top of the article, return that URL; otherwise null.\n"
        "4) If any field is unknown, set it to null.\n"
        "5) Ignore navigation, ads, footer, or sidebar content.\n"
        "6) Output must be valid JSON, no extra text or code fences.\n"
        "7) Provide a corresponding title and author (if author is available in the JSON); else null.\n"
        f"Topic: {topic_desc}\n"
        f"Article JSON: {content_json}"
    )
    return conversation_service.request_ai(base_prompt)