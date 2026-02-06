from serpapi import GoogleSearch
from app.core.config import settings

def search_serp_with_topic_description(description: str):
	params = {
		"engine": "google",
		"q": description,
		"location": "Austin, Texas, United States",
		"google_domain": "google.com",
		"hl": "en",
		"gl": "us",
		"api_key": settings.SERP_API_KEY
	}
	search = GoogleSearch(params)
	results = search.get_dict()
	print(results)
	return results
