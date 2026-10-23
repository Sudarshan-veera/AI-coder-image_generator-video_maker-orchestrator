"""Each agent must be an orchestrator that runs its documented tasks and writes its own trace."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from fakes import FakeImageGen, FakeTTS, fake_llm
import logo_agent as L
import video_agent as V


def ok_tasks(path):
    ev = json.load(open(path))
    return ev, {e["task"] for e in ev if e["status"] == "ok"}


def test_image_agent_runs_its_tasks(tmp_path):
    L.LogoAgent(llm=fake_llm("emblem"), imagegen=FakeImageGen([9]), team="T", outdir=str(tmp_path)).run()
    ev, ok = ok_tasks(tmp_path / "image_agent_trace.json")
    assert {"brand_analysis", "design_concepts", "generate", "evaluate", "finalize"} <= ok
    assert all(e["agent"] == "image_agent" for e in ev)
    assert [e["status"] for e in ev if e["task"] == "refine"] == ["skipped"]


def test_video_agent_runs_its_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, check: None)
    V.VideoAgent(imagegen=FakeImageGen(), tts=FakeTTS(), llm=fake_llm("x"),
                 outdir=str(tmp_path), n_scenes=2).run()
    ev, ok = ok_tasks(tmp_path / "video_agent_trace.json")
    assert {"plan_scenes", "art", "evaluate_frame", "compose_frame", "narrate",
            "render_clip", "assemble"} <= ok
    assert sum(1 for e in ev if e["task"] == "art") == 2
    assert all(e["agent"] == "video_agent" for e in ev)
