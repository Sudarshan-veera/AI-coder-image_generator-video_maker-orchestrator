from ddgs import DDGS
import trafilatura


def web_search(query, n=8):
    try:
        with DDGS() as d:
            return [{"title": r.get("title", ""), "url": r.get("href", ""),
                     "snippet": r.get("body", "")} for r in d.text(query, max_results=n)]
    except Exception as e:
        print(f"[web_search] {e}")
        return []


def news_search(query, n=8):
    try:
        with DDGS() as d:
            return [{"title": r.get("title", ""), "url": r.get("url", ""),
                     "snippet": r.get("body", ""), "date": r.get("date", "")}
                    for r in d.news(query, max_results=n)]
    except Exception as e:
        print(f"[news_search] {e}")
        return []


def fetch_page(url, limit=3000):
    try:
        html = trafilatura.fetch_url(url)
        text = trafilatura.extract(html) if html else ""
        return (text or "")[:limit]
    except Exception:
        return ""
