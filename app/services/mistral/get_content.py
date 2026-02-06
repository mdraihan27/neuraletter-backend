from app.services.mistral.conversation_service import MistralConversationService

conversation_service = MistralConversationService()


def get_content_json(topic_desc: str, content_json: str):
    """
    Summarize article content based on topic relevance.
    Uses chunking for long articles.
    
    Args:
        topic_desc: The topic to focus the summary on
        content_json: JSON string of scraped article content
        
    Returns:
        JSON string with structured article data (title, author, summary, key_points, date, lead_image)
    """
    base_prompt = (
        "You are an article summarization assistant. Analyze the provided JSON and return ONLY a single JSON object (no prose, no code blocks).\n"
        "Expected output shape: {\"title\": string|null, \"author\": string|null, \"date\": string|null, \"summary\": string|null, \"key_points\": [string], \"lead_image\": string|null, \"relevant\": boolean}.\n"
        "I will also provide a topic. The summary you provide must align with the topic and focus on relevant information.\n"
        "Requirements:\n"
        "1) If the article truly contains NO meaningful information related to the topic (for example a 404 page, generic error, or content that never mentions the topic or any of its key entities), set relevant=false and set title, author, date, summary, lead_image to null and key_points to an empty list []. Do NOT invent content.\n"
        "2) If the article contains ANY non-trivial information that helps understand the topic or its context, set relevant=true and summarize ONLY the parts related to the topic.\n"
        "3) When relevant=true, keep summary concise but comprehensive (3-6 sentences focused on topic relevance).\n"
        "4) key_points should be 3-7 short bullet-like strings covering the main takeaways related to the topic.\n"
        "5) lead_image: extract any prominent image URL from the content; otherwise null.\n"
        "6) date: extract publication date if available (ISO format preferred); otherwise null.\n"
        "7) If any field is unknown, set it to null.\n"
        "8) Ignore navigation, ads, footer, or sidebar content.\n"
        "9) Output must be valid JSON, no extra text or code fences. Do NOT output explanatory sentences like 'the content does not contain usable information' as the summary.\n"
        "10) Provide a corresponding title and author (if available in the JSON); else null.\n"
        "11) Focus the summary on how the content relates to the specified topic.\n"
        f"Topic: {topic_desc}\n"
        f"Article JSON: {{DATA}}"
    )
    
    try:
        # Use chunking for long articles
        result = conversation_service.request_ai_with_chunking(base_prompt, content_json, max_chars=12000)
        print(f"Generated summary for topic '{topic_desc}'")
        return result
    except Exception as e:
        print(f"Error generating content summary: {str(e)}")
        # Return minimal valid JSON on error
        return '{"title": null, "author": null, "date": null, "summary": "Error processing content", "key_points": [], "lead_image": null}'