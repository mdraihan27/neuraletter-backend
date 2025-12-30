from app.services.mistral.conversation_service import MistralConversationService

conversation_service = MistralConversationService()


def get_base_urls(topic: str):
    base_prompt = (
        "You are a web research assistant. Given a topic, return exactly 3 working, reputable base URLs directly related to it.\n"
        "Rules:\n"
        "1. Output must be a python list of those urls, no other text, just a python list.\n"
        "2. Use base/home URLs (e.g., https://example.com), not article subpages or query strings.\n"
        "3. Prefer diverse domains; avoid more than one URL from the same site.\n"
        "4. Only include real, accessible sites (no broken links, parked domains, or login-only pages).\n"
        "5. No extra text, explanations, or trailing punctuation.\n"
        "Topic: "
    )
    result =  conversation_service.request_ai(base_prompt + topic)
    # print("URL List:\n"+result)
    return result