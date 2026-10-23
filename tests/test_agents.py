import json, os
import agents as A


def make(name, mentions=1, score=None):
    c = {"name": name, "mentions": mentions, "sources": ["http://s/" + name]}
    if score is not None:
        c["score"] = score
    return c


def test_planner_uses_llm_queries(monkeypatch):
    monkeypatch.setattr(A, "llm_json", lambda s, u: {"queries": ["q1", "q2"]})
    assert A.planner("FinTech") == ["q1", "q2"]


def test_planner_falls_back_when_llm_returns_nothing(monkeypatch):
    monkeypatch.setattr(A, "llm_json", lambda s, u: {})
    qs = A.planner("FinTech")
    assert len(qs) >= 3 and all("FinTech" in q for q in qs)


def test_researcher_dedupes_urls(monkeypatch):
    r = {"title": "t", "url": "http://a", "snippet": "s"}
    monkeypatch.setattr(A, "web_search", lambda q: [r])
    monkeypatch.setattr(A, "news_search", lambda q, n=5: [r])
    monkeypatch.setattr(A, "fetch_page", lambda u: "page text")
    docs = A.researcher(["q1", "q2"])
    assert len(docs) == 1 and docs[0]["text"] == "page text"


def test_extractor_merges_duplicates(monkeypatch):
    monkeypatch.setattr(A, "llm_json", lambda s, u: {"startups": [{"name": "Stripe"}, {"name": " stripe "}]})
    docs = [{"title": "a", "snippet": "", "url": "http://1"}, {"title": "b", "snippet": "", "url": "http://2"}]
    out = A.extractor("FinTech", docs)
    assert len(out) == 1
    assert out[0]["mentions"] == 4 and len(out[0]["sources"]) == 2


def test_extractor_skips_nameless(monkeypatch):
    monkeypatch.setattr(A, "llm_json", lambda s, u: {"startups": [{"what_it_does": "x"}]})
    assert A.extractor("FinTech", [{"title": "a", "snippet": "", "url": "u"}]) == []


def test_ranker_orders_by_score(monkeypatch):
    monkeypatch.setattr(A, "llm_json", lambda s, u: {"ranking": [
        {"name": "Low", "score": 5, "reason": "r"}, {"name": "High", "score": 9, "reason": "r"}]})
    ranked = A.ranker("FinTech", [make("Low"), make("High")])
    assert [c["name"] for c in ranked] == ["High", "Low"]


def test_ranker_survives_bad_scores(monkeypatch):
    monkeypatch.setattr(A, "llm_json", lambda s, u: {"ranking": [{"name": "X", "score": "n/a"}]})
    assert A.ranker("FinTech", [make("X")])[0]["score"] >= 0


def test_critic_flags_short_list():
    assert any("only 3" in i for i in A.critic([make(str(i), score=1) for i in range(3)]))


def test_critic_flags_missing_sources():
    top = [make(str(i), score=1) for i in range(10)]
    top[0]["sources"] = []
    assert any("no source" in i for i in A.critic(top))


def test_critic_passes_good_list():
    assert A.critic([make(str(i), score=1) for i in range(10)]) == []


def test_reporter_writes_md_and_json(tmp_path):
    top = [make("Stripe", score=9.0)]
    top[0].update(what_it_does="payments", funding="$2B", valuation="$90B", latest_news="n")
    md = A.reporter("Fin Tech", top, outdir=str(tmp_path))
    assert os.path.exists(md) and "Stripe" in open(md).read()
    assert json.load(open(tmp_path / "fin_tech_top10.json"))[0]["name"] == "Stripe"


def test_llm_json_extracts_json_from_noisy_text(monkeypatch):
    class R(dict):
        pass
    monkeypatch.setattr(A.ollama, "chat",
                        lambda **kw: {"message": {"content": 'Sure! {"queries": ["a"]} done'}})
    assert A.llm_json("s", "u") == {"queries": ["a"]}


def test_llm_json_returns_empty_after_retries(monkeypatch):
    monkeypatch.setattr(A.ollama, "chat", lambda **kw: {"message": {"content": "no json here"}})
    assert A.llm_json("s", "u", retries=2) == {}
