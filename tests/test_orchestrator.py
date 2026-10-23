import json
import agents as A
import orchestrator as O

EXPECTED = ["plan", "research", "extract", "filter", "rank", "enrich", "critic"]


def cand(i, **kw):
    c = {"name": f"S{i}", "mentions": 1, "sources": [f"http://s/{i}"], "what_it_does": "x",
         "total_funding": "$100M", "valuation": f"${i + 1}B", "status": "private",
         "latest_news": "n", "score": 100 - i}
    c.update(kw)
    return c


def patch_common(mp):
    mp.setattr(A, "planner", lambda c, r=1: ["q"])
    mp.setattr(A, "researcher", lambda q: [])
    mp.setattr(A, "enricher", lambda c, top: top)
    mp.setattr(A, "ranker", lambda c, cands: sorted(cands, key=lambda x: -x["score"]))


def test_task_list_matches_design():
    assert [t.name for t in O.build_tasks()] == EXPECTED


def test_pipeline_end_to_end_and_trace(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    patch_common(monkeypatch)
    monkeypatch.setattr(A, "extractor", lambda c, d: [cand(i) for i in range(12)])
    O.run("FinTech")
    assert len(json.load(open(tmp_path / "outputs" / "fintech_top10.json"))) == 10
    trace = json.load(open(tmp_path / "outputs" / "trace.json"))
    assert all(e["agent"] == "startup_agent" for e in trace)
    assert {t for t in EXPECTED + ["report"]} <= {e["task"] for e in trace if e["status"] == "ok"}


def test_public_companies_never_reach_ranker(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    patch_common(monkeypatch)
    seen = {}
    monkeypatch.setattr(A, "extractor", lambda c, d: [cand(i) for i in range(11)]
                        + [cand(50, name="PubCo", status="public"),
                           cand(51, name="Listed", valuation="$9B listed on NYSE")])
    monkeypatch.setattr(A, "ranker", lambda c, cands: seen.setdefault("n", [x["name"] for x in cands]) and cands)
    O.run("FinTech")
    assert "PubCo" not in seen["n"] and "Listed" not in seen["n"]


def test_retries_when_critic_fails_then_stops_at_max_rounds(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    patch_common(monkeypatch)
    calls = {"n": 0}

    def planner(c, r=1):
        calls["n"] += 1
        return ["q"]
    monkeypatch.setattr(A, "planner", planner)
    monkeypatch.setattr(A, "extractor", lambda c, d: [cand(i) for i in range(3)])  # too few
    O.run("FinTech")
    assert calls["n"] == O.MAX_ROUNDS
    assert "Data quality warnings" in open(tmp_path / "outputs" / "fintech_top10.md").read()


def test_cross_round_merge_does_not_duplicate(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    patch_common(monkeypatch)
    monkeypatch.setattr(A, "extractor", lambda c, d: [cand(i) for i in range(3)])
    seen = []
    monkeypatch.setattr(A, "ranker", lambda c, cands: (seen.append(len(cands)) or cands))
    O.run("FinTech")
    assert seen and all(n == 3 for n in seen)
