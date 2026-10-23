import json
import pytest
from common.orchestrator import Orchestrator, Task, TaskError


def test_context_flows_between_tasks():
    o = Orchestrator("a")
    ctx = o.run([Task("one", lambda c: {"x": 1}), Task("two", lambda c: {"y": c["x"] + 1})], {})
    assert ctx == {"x": 1, "y": 2}


def test_retry_then_success():
    calls = {"n": 0}

    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("boom")
        return {"ok": True}
    o = Orchestrator("a")
    ctx = o.run([Task("flaky", flaky, retries=1)], {})
    assert ctx["ok"] and [e["status"] for e in o.events] == ["failed", "ok"]


def test_retries_exhausted_raises_taskerror():
    def bad(ctx):
        raise ValueError("nope")
    with pytest.raises(TaskError):
        Orchestrator("a").run([Task("bad", bad, retries=1)], {})


def test_optional_failure_is_recorded_and_skipped_over():
    def bad(ctx):
        raise ValueError("nope")
    o = Orchestrator("a")
    ctx = o.run([Task("bad", bad, optional=True), Task("next", lambda c: {"ran": True})], {})
    assert ctx["ran"] and o.events[0]["status"] == "failed"


def test_when_skips_task():
    o = Orchestrator("a")
    ctx = o.run([Task("skip", lambda c: {"x": 1}, when=lambda c: False)], {})
    assert "x" not in ctx and o.events[0]["status"] == "skipped"


def test_loop_stops_when_done():
    o = Orchestrator("a")
    ctx = o.loop([Task("inc", lambda c: {"n": c.get("n", 0) + 1})], {}, lambda c: c["n"] >= 2, 5)
    assert ctx["n"] == 2 and ctx["round"] == 2


def test_loop_respects_max_rounds():
    o = Orchestrator("a")
    ctx = o.loop([Task("inc", lambda c: {"n": c.get("n", 0) + 1})], {}, lambda c: False, 3)
    assert ctx["n"] == 3


def test_trace_saved_with_timing_and_agent_name(tmp_path):
    p = tmp_path / "t" / "trace.json"
    o = Orchestrator("my_agent", str(p))
    o.run([Task("one", lambda c: None)], {})
    o.save()
    ev = json.load(open(p))
    assert ev[0]["agent"] == "my_agent" and ev[0]["task"] == "one" and "seconds" in ev[0]
