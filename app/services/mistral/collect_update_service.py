import ast
import json
import re
from datetime import datetime
from threading import Timer

from app.db.session import SessionLocal
from app.models.topic import Topic
from app.models.update import Update
from app.services.mistral.get_base_urls import get_base_urls
from app.services.mistral.get_relevent_urls import get_relevant_urls
from app.services.playwright.fetch_html import collect_text_and_links
from app.services.mistral.get_content import get_content_json
from app.utils.random_generator import generate_random_string


def _parse_urls(text_or_list):
    """Best-effort parse of URLs from a list or text blob."""
    if isinstance(text_or_list, list):
        return [u for u in text_or_list if isinstance(u, str) and u.strip()]

    if not text_or_list:
        return []

    # Try to parse Python literal list first
    if isinstance(text_or_list, str):
        try:
            parsed = ast.literal_eval(text_or_list)
            if isinstance(parsed, list):
                return [u for u in parsed if isinstance(u, str) and u.strip()]
        except Exception:
            pass

        # Fallback: regex extract
        return re.findall(r"https?://[^\s,\]\)\"]+", text_or_list)

    return []


def _parse_date_to_epoch_ms(date_str):
    """Convert ISO 8601 date string to epoch milliseconds, or None on failure."""
    if not date_str:
        return None
    try:
        cleaned = str(date_str).strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return int(dt.timestamp() * 1000)
    except Exception as e:
        print("_parse_date_to_epoch_ms error:", e)
        return None


def _save_update_to_db(topic:Topic, content_dict):
    """Persist the final content JSON into the updates table.

    - Stores key_points as a JSON array string.
    - Uses the topic string as associated_topic_id for now.
    - Rolls back the transaction on any DB error.
    """
    db = SessionLocal()
    try:
        key_points_value = content_dict.get("key_points")
        if not isinstance(key_points_value, list):
            key_points_value = []
        key_points_str = json.dumps(key_points_value, ensure_ascii=False)

        date_ms = _parse_date_to_epoch_ms(content_dict.get("date"))

        new_update = Update(
            id=generate_random_string(32),
            associated_topic_id=str(topic.id),
            title=content_dict.get("title"),
            author=content_dict.get("author"),
            summary=content_dict.get("summary"),
            date=date_ms,
            key_points=key_points_str,
            image_link=content_dict.get("lead_image") or "",
        )

        db.add(new_update)
        db.commit()
    except Exception as e:
        db.rollback()
        print("_save_update_to_db error:", e)
    finally:
        db.close()


def get_links_task(topic:Topic):
    try:
        result_text = get_base_urls(topic.description)
        urls = _parse_urls(result_text)
        print("Links:\n", urls)
        Timer(14, visit_links_task, args=(topic, urls)).start()
        return urls
    except Exception as e:
        print("get_links_task error:", e)
        return None

def visit_links_task(topic:Topic, urls:list):
    try:
        result = collect_text_and_links(urls, False)
        print("Links JSON\n", json.dumps(result, ensure_ascii=False))
        Timer(14, get_relevant_urls_task, args=(topic, result)).start()
        return result
    except Exception as e:
        print("visit_links_task error:", e)
        return None

def get_relevant_urls_task(topic:Topic, json_content:str):
    try:
        content_str = json.dumps(json_content, ensure_ascii=False) if not isinstance(json_content, str) else json_content
        result_text = get_relevant_urls(topic.description, content_str)
        urls = _parse_urls(result_text)
        print("Relevant URLS\n", urls)
        Timer(14, visit_each_article_link_task, args=(topic, urls)).start()
        return urls
    except Exception as e:
        print("get_relevant_urls_task error:", e)
        return None

def visit_each_article_link_task(topic:Topic, urls:list):
    try:
        result = collect_text_and_links(urls)
        print("Relevant URLS Body\n", json.dumps(result, ensure_ascii=False))
        Timer(14, get_content_task, args=(topic, result)).start()
        return result
    except Exception as e:
        print("visit_each_article_link_task error:", e)
        return None

def get_content_task(topic:Topic, content_json:str):
    try:
        content_str = json.dumps(content_json, ensure_ascii=False) if not isinstance(content_json, str) else content_json
        result = get_content_json(topic.description, content_str)

        # Ensure we have a Python dict from the AI response
        content_dict = None
        if isinstance(result, dict):
            content_dict = result
        elif isinstance(result, str):
            try:
                cleaned = result.strip()
                # Strip optional Markdown code fences like ```json ... ```
                if cleaned.startswith("```"):
                    # Remove first fence line
                    cleaned = re.sub(r"^```[a-zA-Z0-9]*\s*", "", cleaned)
                    # Remove trailing fence if present
                    if cleaned.endswith("```"):
                        cleaned = cleaned[: cleaned.rfind("```")].strip()

                content_dict = json.loads(cleaned)
            except Exception as e:
                print("get_content_task JSON parse error:", e)

        print("Final Content", result)

        # Only attempt to save if we parsed valid JSON
        if isinstance(content_dict, dict):
            _save_update_to_db(topic, content_dict)

        return result
    except Exception as e:
        print("get_content_task error:", e)
        return None


def combined_task(topic:Topic):
    get_links_task(topic)
    return "LAUNCHED"

# if __name__ == "__collect_update_service__":
#
#     combined_task("Update of Dhaka, Bangladesh weather of upcoming 10 days including temperature, humidity, wind speed and chance of rain.")
