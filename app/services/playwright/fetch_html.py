import json
from playwright.sync_api import sync_playwright

URLS = [
    "https://prothomalo.com",
]



def collect_text_and_links(urls, headless=True):
    headless=False
    """Collect plain text sections and associated links from pages into a JSON file."""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for url in urls:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            data = page.evaluate(
                r"""
                () => {
                    const stripNodes = [
                        "script", "style", "noscript", "iframe", "svg", "canvas",
                        "picture", "source", "template"
                    ];
                    stripNodes.forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));

                    const clean = (text) => text.replace(/\s+/g, " ").trim();

                    const blocks = document.querySelectorAll(
                        "article, main, section, p, h1, h2, h3, h4, h5, h6, li, blockquote"
                    );

                    const sections = [];

                    blocks.forEach(el => {
                        const text = clean(el.innerText || "");
                        if (!text) return;

                        const links = Array.from(el.querySelectorAll("a[href]")).map(a => ({
                            text: clean(a.innerText || a.textContent || ""),
                            url: a.href.trim(),
                        })).filter(link => link.text && link.url);

                        sections.push({ text, links });
                    });

                    return { url: window.location.href, sections };
                }
                """
            )
        results.append(data)

    return results


