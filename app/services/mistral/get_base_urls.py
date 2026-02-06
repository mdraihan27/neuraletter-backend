from app.services.mistral.conversation_service import MistralConversationService

conversation_service = MistralConversationService()


def get_base_urls(topic: str):
    """
    Get base URLs relevant to a topic from AI.
    Returns 5 diverse, reputable URLs to start the content collection.
    """
    base_prompt = (
        "You are a web research assistant. Given a topic, return exactly 5 working, reputable base URLs that are the BEST starting points to discover recent, in‑depth articles about that topic.\n"
        "Rules:\n"
        "1. Output must be a Python list of those URLs, no other text, just a Python list like ['url1', 'url2', ...].\n"
        "2. Choose pages that list or aggregate news/articles SPECIFICALLY about the topic (e.g., a dedicated topic or search page), not generic homepages.\n"
        "3. Prefer diverse domains; avoid more than one URL from the same site.\n"
        "4. Only include real, accessible sites (no broken links, parked domains, or login-only pages).\n"
        "5. Prioritize authoritative news sites, official sources, and well-known publications over blogs or low‑quality sites.\n"
        "6. Avoid social networks, YouTube, and generic front pages unless they are clearly focused on the topic.\n"
        "7. No extra text, explanations, or trailing punctuation.\n"
        "Topic: "
    )
    
    try:
        result = conversation_service.request_ai(base_prompt + topic)
        print(f"Base URLs for topic '{topic}':\n{result}")
        return result
    except Exception as e:
        print(f"Error getting base URLs: {str(e)}")
        # Return empty list on error
        return "[]"