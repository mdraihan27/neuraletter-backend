import json
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URLS = [
    "https://prothomalo.com",
]


def collect_text_and_links(urls, headless=True, max_retries=3, timeout=60000):
    """
    Collect plain text sections and associated links from pages into a JSON structure.
    
    Args:
        urls: List of URLs to scrape
        headless: Whether to run browser in headless mode
        max_retries: Number of retry attempts per URL
        timeout: Timeout in milliseconds for page load
        
    Returns:
        List of dictionaries with url, sections, and optional error information
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for url in urls:
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    print(f"Attempting to load {url} (attempt {retry_count + 1}/{max_retries})")
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                    
                    # Wait a bit for dynamic content
                    time.sleep(2)

                    data = page.evaluate(
                        r"""
                        () => {
                            const stripNodes = [
                                "script", "style", "noscript", "iframe", "svg", "canvas",
                                "picture", "source", "template", "nav", "footer", "aside"
                            ];
                            stripNodes.forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));

                            const clean = (text) => text.replace(/\s+/g, " ").trim();

                            const blocks = document.querySelectorAll(
                                "article, main, section, p, h1, h2, h3, h4, h5, h6, li, blockquote"
                            );

                            const sections = [];
                            const seenTexts = new Set();

                            blocks.forEach(el => {
                                const text = clean(el.innerText || "");
                                if (!text || text.length < 10 || seenTexts.has(text)) return;
                                
                                seenTexts.add(text);

                                const links = Array.from(el.querySelectorAll("a[href]")).map(a => ({
                                    text: clean(a.innerText || a.textContent || ""),
                                    url: a.href.trim(),
                                })).filter(link => link.text && link.url && link.url.startsWith("http"));

                                // Extract images from the section
                                const images = Array.from(el.querySelectorAll("img[src]")).map(img => ({
                                    src: img.src,
                                    alt: img.alt || ""
                                })).filter(img => img.src && img.src.startsWith("http"));

                                sections.push({ text, links, images });
                            });

                            return { url: window.location.href, sections };
                        }
                        """
                    )
                    
                    results.append(data)
                    success = True
                    print(f"Successfully scraped {url}")
                    
                except PlaywrightTimeoutError:
                    retry_count += 1
                    print(f"Timeout loading {url}, retry {retry_count}/{max_retries}")
                    if retry_count >= max_retries:
                        results.append({
                            "url": url,
                            "error": "Timeout after multiple retries",
                            "sections": []
                        })
                        
                except Exception as e:
                    retry_count += 1
                    print(f"Error loading {url}: {str(e)}, retry {retry_count}/{max_retries}")
                    if retry_count >= max_retries:
                        results.append({
                            "url": url,
                            "error": str(e),
                            "sections": []
                        })

        browser.close()

    return results
