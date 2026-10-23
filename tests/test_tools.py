import tools


def test_fetch_page_returns_empty_on_error(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(tools.trafilatura, "fetch_url", boom)
    assert tools.fetch_page("http://x") == ""


def test_fetch_page_truncates(monkeypatch):
    monkeypatch.setattr(tools.trafilatura, "fetch_url", lambda u: "<html/>")
    monkeypatch.setattr(tools.trafilatura, "extract", lambda h: "a" * 5000)
    assert len(tools.fetch_page("http://x", limit=100)) == 100


def test_web_search_handles_failure(monkeypatch):
    class Bad:
        def __enter__(self):
            raise RuntimeError("rate limited")
        def __exit__(self, *a):
            return False
    monkeypatch.setattr(tools, "DDGS", Bad)
    assert tools.web_search("fintech") == []
    assert tools.news_search("fintech") == []
