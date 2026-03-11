"""
tools.py — ScholarFlow AI
Web search (Tavily) and full-page scraper (BeautifulSoup) tools.
"""
import os
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

_tavily_client = None


def _get_tavily_client() -> TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables.")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using Tavily AI search API.
    Returns a list of dicts: [{title, url, content}, ...]
    """
    try:
        # Sanitize and truncate query (Max 400 per Tavily error logs)
        query = query.replace("#", "").replace("*", "").replace("_", "").replace("`", "").strip()
        if len(query) > 380:
            query = query[:380]
            
        client = _get_tavily_client()
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            })
        return results
    except Exception as e:
        print(f"[Tavily Search Error] {e}")
        return []


def scrape_page(url: str, max_chars: int = 8000) -> str:
    """
    Scrape a full web page and return clean text content.
    Uses BeautifulSoup to strip scripts, styles, and navigation.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "advertisement", "iframe", "noscript"]):
            tag.decompose()

        # Extract meaningful content from article/main/body tags (priority order)
        content_tags = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id="content")
            or soup.find(class_="content")
            or soup.body
        )

        if content_tags:
            text = content_tags.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Collapse excessive blank lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        return clean_text[:max_chars]

    except Exception as e:
        print(f"[Scraper Error] {url} — {e}")
        return f"[Could not scrape page: {e}]"


def research_web(topic: str, outline: str) -> dict:
    """
    High-level research function: searches Tavily, scrapes top URLs,
    returns structured research data with citations.
    """
    display_topic = topic[:100] + "..." if len(topic) > 100 else topic
    print(f"[Researcher] Searching Tavily for: {display_topic}")
    search_results = tavily_search(f"peer-reviewed research {topic}", max_results=5)

    if not search_results:
        search_results = tavily_search(topic, max_results=5)

    scraped_data = []
    urls_scraped = []

    for result in search_results[:4]:  # Scrape top 4 URLs
        url = result["url"]
        print(f"[Researcher] Scraping: {url}")
        full_text = scrape_page(url)
        scraped_data.append({
            "title": result["title"],
            "url": url,
            "snippet": result["content"],
            "full_text": full_text,
        })
        urls_scraped.append(url)

    return {
        "sources": scraped_data,
        "urls": urls_scraped,
    }
