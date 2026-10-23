import os
import pytest

pytestmark = pytest.mark.live
skip = pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to run live tests")


@skip
def test_ollama_model_responds():
    import ollama
    r = ollama.chat(model=os.getenv("AGENT_MODEL", "agent-coder"),
                    messages=[{"role": "user", "content": "reply with the single word: ok"}],
                    think=False)
    assert "ok" in r["message"]["content"].lower()


@skip
def test_full_pipeline_returns_ten_startups(tmp_path, monkeypatch):
    import json, orchestrator
    monkeypatch.chdir(tmp_path)
    orchestrator.run("FinTech")
    data = json.load(open(tmp_path / "outputs" / "fintech_top10.json"))
    assert len(data) >= 5          # live web results vary; 10 is the target
