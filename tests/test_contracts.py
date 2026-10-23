"""Each agent must be an orchestrator that runs its independent tasks, recorded in its own trace."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from fakes import FakeClient, text_resp, img_resp
import logo_agent as L
import video_agent as V

SCENE = {"subject": "A user", "action": "types", "scene": "desk", "style": "flat",
         "camera": "close-up", "dialogue": "Hi.", "sound_effects": "typing"}


def ok_tasks(path):
    ev = json.load(open(path))
    return ev, {e["task"] for e in ev if e["status"] == "ok"}


def test_image_agent_runs_its_tasks(tmp_path):
    rs = [text_resp("brand"), text_resp("prompt"), img_resp(), text_resp('{"score": 9}')]
    L.LogoAgent(client=FakeClient(rs), team="T", outdir=str(tmp_path)).run()
    ev, ok = ok_tasks(tmp_path / "image_agent_trace.json")
    assert {"brand_analysis", "design_concepts", "generate", "evaluate", "finalize"} <= ok
    assert all(e["agent"] == "image_agent" for e in ev)
    assert [e["status"] for e in ev if e["task"] == "refine"] == ["skipped"]


def test_video_agent_runs_its_tasks(tmp_path, monkeypatch):
    rs = [text_resp(json.dumps({"scenes": [SCENE, SCENE]}))]
    for _ in range(2):
        rs += [img_resp(), text_resp("9")]
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, check: None)
    V.VideoAgent(client=FakeClient(rs), outdir=str(tmp_path), n_scenes=2, poll=0).run()
    ev, ok = ok_tasks(tmp_path / "video_agent_trace.json")
    assert {"plan_scenes", "scene_image", "evaluate_frame", "collect_frame",
            "scene_video", "assemble"} <= ok
    assert sum(1 for e in ev if e["task"] == "scene_image") == 2
    assert all(e["agent"] == "video_agent" for e in ev)
