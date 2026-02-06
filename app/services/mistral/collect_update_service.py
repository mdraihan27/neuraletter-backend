import ast
import json
import re
from datetime import datetime
from sqlalchemy.orm import Session

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


def _post_filter_relevant_urls(urls, topic_description: str, max_urls: int = 10):
    """Heuristically rank and filter article URLs to better match the topic.

    - Deduplicates while preserving order.
    - Scores URLs higher if they contain topic keywords, look like article
      pages (deep paths, slugs, or dates), and are https.
    - Filters out very low‑scoring URLs (likely home/category pages).
    """

    if not urls:
        return []

    # Unique while preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        if not isinstance(u, str):
            continue
        u = u.strip()
        if not u or u in seen:
            continue
        seen.add(u)
        unique_urls.append(u)

    topic = (topic_description or "").lower()
    # Basic keyword extraction from topic
    raw_keywords = re.split(r"[^a-zA-Z0-9]+", topic)
    keywords = [k for k in raw_keywords if len(k) >= 4]

    scored = []
    for idx, u in enumerate(unique_urls):
        url_l = u.lower()
        score = 0

        if url_l.startswith("https://"):
            score += 1

        # Reward article‑like paths: multiple segments, slugs, or dates
        path = url_l.split("//", 1)[-1].split("/", 1)[-1]
        segments = [s for s in path.split("/") if s]
        if len(segments) >= 3:
            score += 2
        if any(ch.isdigit() for ch in path) and any(y in path for y in ["/20", "-20"]):
            score += 2

        # Reward topic keywords appearing in URL
        for k in keywords:
            if k in url_l:
                score += 2

        # Penalize obvious non‑article areas
        if any(bad in url_l for bad in ["/tag/", "/category/", "/topics/", "login", "signup", "account"]):
            score -= 2

        scored.append((score, idx, u))

    # Keep URLs with positive score; if none, fall back to original list
    positive = [t for t in scored if t[0] > 0]
    if positive:
        # Sort by score desc, then original index
        positive.sort(key=lambda t: (-t[0], t[1]))
        ordered = [u for _, _, u in positive]
    else:
        ordered = [u for _, _, u in sorted(scored, key=lambda t: t[1])]

    return ordered[:max_urls]


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
        print(f"Date parsing error: {e}")
        return None


def _shrink_article_for_ai(article: dict, max_total_chars: int = 8000) -> dict:
    """Return a trimmed copy of the scraped article so AI input stays small.

    We keep the original order of sections but only include as much text as
    needed up to ``max_total_chars`` characters. Links/images are preserved
    for included sections so the model still has context.
    """

    if not isinstance(article, dict):
        return article

    sections = article.get("sections") or []
    if not isinstance(sections, list) or not sections:
        return article

    remaining = max_total_chars
    trimmed_sections = []

    for section in sections:
        if remaining <= 0:
            break

        text = section.get("text") or ""
        if not isinstance(text, str):
            continue

        text = text.strip()
        if not text:
            continue

        if len(text) <= remaining:
            use_text = text
        else:
            # Truncate long sections and stop afterwards.
            use_text = text[:remaining]

        trimmed_sections.append(
            {
                "text": use_text,
                "links": section.get("links") or [],
                "images": section.get("images") or [],
            }
        )

        remaining -= len(use_text)

    # If for some reason nothing was added, fall back to original.
    if not trimmed_sections:
        return article

    trimmed = dict(article)
    trimmed["sections"] = trimmed_sections
    return trimmed


def _save_update_to_db(topic: Topic, content_dict: dict, db: Session):
    """
    Persist the final content JSON into the updates table.
    
    Args:
        topic: Topic object
        content_dict: Dictionary with content fields
        db: Database session
        
    Returns:
        Update object if successful, None otherwise
    """
    try:
        key_points_value = content_dict.get("key_points")
        if not isinstance(key_points_value, list):
            key_points_value = []
        key_points_str = json.dumps(key_points_value, ensure_ascii=False)

        date_ms = _parse_date_to_epoch_ms(content_dict.get("date"))

        new_update = Update(
            id=generate_random_string(32),
            associated_topic_id=str(topic.id),
            title=content_dict.get("title") or "Untitled",
            author=content_dict.get("author"),
            summary=content_dict.get("summary") or "",
            date=date_ms,
            key_points=key_points_str,
            image_link=content_dict.get("lead_image") or "",
        )

        db.add(new_update)
        db.commit()
        db.refresh(new_update)
        
        print(f"✓ Saved update: {new_update.title}")
        return new_update
        
    except Exception as e:
        db.rollback()
        print(f"Error saving update to database: {e}")
        return None


def collect_updates_for_topic(topic: Topic, db: Session):
    """
    Main pipeline to collect and summarize content for a topic.
    
    Pipeline:
    1. Get base URLs from AI based on topic
    2. Scrape those URLs to collect links and text
    3. Filter relevant article links using AI
    4. Scrape article content
    5. Summarize content using AI
    6. Save to database
    
    Args:
        topic: Topic object with description
        db: Database session
        
    Returns:
        Dictionary with status and results
    """
    print(f"[pipeline] Starting update collection for topic_id={topic.id}, description={topic.description!r}")

    results = {
        "status": "started",
        "topic_id": topic.id,
        "topic_description": topic.description,
        "steps": [],
        "updates_created": [],
        "errors": []
    }
    
    try:
        # Step 1: Get base URLs from AI
        print(f"\n{'='*60}")
        print(f"[pipeline] STEP 1: Getting base URLs for topic: {topic.description}")
        print(f"{'='*60}")
        
        print("[pipeline] Calling get_base_urls()")
        base_urls_text = get_base_urls(topic.description)
        print(f"[pipeline] Raw base_urls_text from AI: {base_urls_text}")
        base_urls = _parse_urls(base_urls_text)
        print(f"[pipeline] Parsed base URLs: {base_urls}")
        
        if not base_urls:
            results["status"] = "failed"
            results["errors"].append("No base URLs returned from AI")
            return results
        
        results["steps"].append({
            "step": 1,
            "name": "Get base URLs",
            "status": "completed",
            "urls_count": len(base_urls),
            "urls": base_urls
        })
        print(f"✓ Found {len(base_urls)} base URLs")
        
        # Step 2: Scrape base URLs
        print(f"\n{'='*60}")
        print(f"[pipeline] STEP 2: Scraping base URLs to collect links")
        print(f"{'='*60}")
        
        print(f"[pipeline] Calling collect_text_and_links() for {len(base_urls)} base URLs")
        scraped_base = collect_text_and_links(base_urls, headless=True)
        print(f"[pipeline] Finished scraping base URLs, got {len(scraped_base)} records")
        
        # Filter out errors
        valid_scraped = [s for s in scraped_base if "error" not in s]
        if not valid_scraped:
            results["status"] = "failed"
            results["errors"].append("Failed to scrape any base URLs")
            return results
        
        results["steps"].append({
            "step": 2,
            "name": "Scrape base URLs",
            "status": "completed",
            "scraped_count": len(valid_scraped),
            "failed_count": len(scraped_base) - len(valid_scraped)
        })
        print(f"✓ Scraped {len(valid_scraped)} pages successfully")
        
        # Step 3: Get relevant article URLs from AI
        print(f"\n{'='*60}")
        print(f"[pipeline] STEP 3: Filtering relevant article URLs using AI")
        print(f"{'='*60}")

        content_json = json.dumps(scraped_base, ensure_ascii=False)
        print(f"[pipeline] Calling get_relevant_urls() with scraped_base JSON of length {len(content_json)}")
        relevant_urls_text = get_relevant_urls(topic.description, content_json)
        print(f"[pipeline] Raw relevant_urls_text from AI: {relevant_urls_text}")
        raw_relevant_urls = _parse_urls(relevant_urls_text)
        print(f"[pipeline] Parsed relevant URLs (raw): {raw_relevant_urls}")

        # Apply local heuristic post‑filtering to make sure we only keep
        # URLs that look article‑like and closely related to the topic.
        relevant_urls = _post_filter_relevant_urls(raw_relevant_urls, topic.description, max_urls=10)
        print(f"[pipeline] Relevant URLs after post‑filtering: {relevant_urls}")
        
        if not relevant_urls:
            results["status"] = "failed"
            results["errors"].append("No relevant article URLs found")
            return results
        
        results["steps"].append({
            "step": 3,
            "name": "Filter relevant URLs",
            "status": "completed",
            "urls_count": len(relevant_urls),
            "urls": relevant_urls
        })
        print(f"✓ Found {len(relevant_urls)} relevant article URLs")
        
        # Step 4: Scrape article content
        print(f"\n{'='*60}")
        print(f"[pipeline] STEP 4: Scraping article content")
        print(f"{'='*60}")

        print(f"[pipeline] Calling collect_text_and_links() for {len(relevant_urls)} article URLs")
        article_content = collect_text_and_links(relevant_urls, headless=True)
        print(f"[pipeline] Finished scraping articles, got {len(article_content)} records")
        
        valid_articles = [a for a in article_content if "error" not in a and a.get("sections")]
        if not valid_articles:
            results["status"] = "failed"
            results["errors"].append("Failed to scrape any article content")
            return results
        
        results["steps"].append({
            "step": 4,
            "name": "Scrape articles",
            "status": "completed",
            "scraped_count": len(valid_articles),
            "failed_count": len(article_content) - len(valid_articles)
        })
        print(f"✓ Scraped {len(valid_articles)} articles successfully")
        
        # Step 5: Summarize and save each article
        print(f"\n{'='*60}")
        print(f"[pipeline] STEP 5: Summarizing articles and saving to database")
        print(f"{'='*60}")
        
        for i, article in enumerate(valid_articles, 1):
            try:
                print(f"[pipeline] Processing article {i}/{len(valid_articles)}: {article['url'][:200]}")
                
                # Trim article content before sending to AI to avoid
                # oversized payloads; this keeps the workflow robust even
                # when pages are very long.
                trimmed_article = _shrink_article_for_ai(article)
                print(f"[pipeline] Trimmed article sections from {len(article.get('sections', []))} to {len(trimmed_article.get('sections', []))}")
                article_json = json.dumps(trimmed_article, ensure_ascii=False)
                print(f"[pipeline] Calling get_content_json() with article JSON length {len(article_json)}")
                summary_result = get_content_json(topic.description, article_json)
                print(f"[pipeline] Raw summary_result from AI (truncated to 500 chars): {str(summary_result)[:500]}")
                
                # Parse the summary JSON
                content_dict = None
                if isinstance(summary_result, dict):
                    content_dict = summary_result
                elif isinstance(summary_result, str):
                    try:
                        cleaned = summary_result.strip()
                        # Strip optional Markdown code fences
                        if cleaned.startswith("```"):
                            cleaned = re.sub(r"^```[a-zA-Z0-9]*\s*", "", cleaned)
                            if cleaned.endswith("```"):
                                cleaned = cleaned[:cleaned.rfind("```")].strip()
                        content_dict = json.loads(cleaned)
                        print("[pipeline] Parsed summary JSON successfully")
                    except Exception as e:
                        print(f"[pipeline] ✗ JSON parse error: {e}")
                        continue
                
                if content_dict and isinstance(content_dict, dict):
                    # Skip only when the AI explicitly marked the article as
                    # not relevant. If 'relevant' is missing, assume it is
                    # relevant and keep a best-effort summary.
                    is_relevant = content_dict.get("relevant")
                    summary_text = (content_dict.get("summary") or "").strip()

                    # Also treat obvious "no usable information" style
                    # boilerplate as non-useful summaries.
                    lowered = summary_text.lower()
                    looks_like_meta = (
                        "does not contain usable information" in lowered
                        or "no substantive data" in lowered
                        or "no relevant content" in lowered
                    )

                    if is_relevant is False or looks_like_meta:
                        print("[pipeline] Skipping article because AI marked it as not relevant or summary is boilerplate")
                        continue

                    # Save to database
                    print("[pipeline] Saving update to database")
                    update = _save_update_to_db(topic, content_dict, db)
                    if update:
                        results["updates_created"].append({
                            "id": update.id,
                            "title": update.title,
                            "url": article["url"]
                        })
                        print(f"[pipeline] ✓ Update created with id={update.id}")
                        
            except Exception as e:
                print(f"[pipeline] ✗ Error processing article: {e}")
                results["errors"].append(f"Article {article['url']}: {str(e)}")
                continue
        
        # Final status
        if results["updates_created"]:
            results["status"] = "completed"
            results["steps"].append({
                "step": 5,
                "name": "Summarize and save",
                "status": "completed",
                "updates_created": len(results["updates_created"])
            })
            print(f"\n{'='*60}")
            print(f"[pipeline] ✓ COMPLETED: Created {len(results['updates_created'])} updates")
            print(f"{'='*60}")
        else:
            results["status"] = "failed"
            results["errors"].append("No updates were created")
            print("[pipeline] ✗ No updates were created for this run")
        
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(f"Pipeline error: {str(e)}")
        print(f"[pipeline] ✗ Pipeline failed: {e}")
    
    return results
