from app.services.mistral.conversation_service import MistralConversationService

conversation_service = MistralConversationService()


def get_relevant_urls(topic_desc: str, content_json: str):
    """
    Filter URLs from scraped content based on topic relevance.
    Uses chunking for large datasets.
    
    Args:
        topic_desc: The topic description to filter against
        content_json: JSON string of scraped content with sections and links
        
    Returns:
        String representation of filtered URL list
    """
    base_prompt = (
        "You are a relevance filter for link extraction. Given a topic and a JSON array of sections (fields 'text' and 'links'), "
        "return URLs for full articles or news stories that are at least moderately related to that topic.\n"
        "Rules:\n"
        "1) Judge relevance using anchor text AND its surrounding section text; ignore nav/ads/footer/legal content.\n"
        "2) Prefer URLs that look like individual article pages (deep paths, slugs, or date segments), not homepages or generic category pages.\n"
        "3) Output exactly a Python list literal of URL strings; no explanations or extra text. Format: ['url1', 'url2', ...]\n"
        "4) Use only URLs from the provided JSON; deduplicate; prefer https; preserve first-seen order.\n"
        "5) Include links where the surrounding text clearly discusses the topic or closely connected events, even if the article is not 100% focused on the topic. Only exclude links that are clearly unrelated.\n"
        "6) Avoid pure navigation links (e.g. generic homepages, section front pages, tag/category indexes) when there are better article candidates available.\n"
        "7) If nothing matches, return an empty list [].\n"
        f"Topic: {topic_desc}\n"
        f"JSON: {{DATA}}\n"
    )

    try:
        # Use chunking for large content
        result = conversation_service.request_ai_with_chunking(base_prompt, content_json, max_chars=15000)
        print(f"Filtered relevant URLs for topic '{topic_desc}'")
        return result
    except Exception as e:
        print(f"Error filtering relevant URLs: {str(e)}")
        return "[]"