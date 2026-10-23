import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from fakes import FakeImageGen, FakeTTS, FakeAnimator, fake_llm
import video_agent as V


def make(tmp_path, scores=None, n=2, llm=None, **kw):
    return V.VideoAgent(imagegen=FakeImageGen(scores), tts=FakeTTS(), llm=llm or fake_llm("x"),
                        outdir=str(tmp_path), n_scenes=n, **kw)


@pytest.fixture
def ffmpeg(monkeypatch):
    calls = []
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, check: calls.append(cmd))
    return calls


def test_plan_has_required_keys_and_respects_limit(tmp_path):
    scenes = make(tmp_path, n=3).plan_scenes()
    assert len(scenes) == 3
    for s in scenes:
        assert {"title", "tasks", "art", "caption", "narration"} <= set(s)


def test_plan_adds_trace_note_when_trace_exists(tmp_path):
    (tmp_path / "trace.json").write_text(json.dumps(
        [{"status": "ok", "seconds": 5.0, "round": 1}, {"status": "ok", "seconds": 7.0, "round": 2}]))
    scenes = make(tmp_path, n=2).plan_scenes()
    assert "2 round(s), 2 tasks, 12 s" in scenes[1]["note"]


def test_polish_accepts_good_rewrite_and_rejects_bad(tmp_path):
    good = " ".join(["word"] * 30)
    a = make(tmp_path, llm=fake_llm(good))
    assert all(s["narration"] == good for s in a.polish_narration(a.plan_scenes()))
    b = make(tmp_path, llm=fake_llm("too short"))
    scenes = b.plan_scenes()
    original = [s["narration"] for s in scenes]
    assert [s["narration"] for s in b.polish_narration(scenes)] == original


def test_polish_survives_llm_failure(tmp_path):
    def down(prompt, **kw):
        raise ConnectionError("down")
    a = make(tmp_path, llm=down)
    assert a.run is not None and a.polish_narration(a.plan_scenes())


def test_full_run_renders_one_clip_per_scene_and_concats(tmp_path, ffmpeg):
    a = make(tmp_path, n=2)
    out = a.run()
    assert out.endswith("how_it_works.mp4")
    assert len(ffmpeg) == 3 and "concat" in ffmpeg[-1]            # 2 clips + 1 concat
    for i in (1, 2):
        assert (tmp_path / "scenes" / f"scene{i}_frame.png").exists()
    assert (tmp_path / "video_plan.json").exists()


def test_weak_frame_is_regenerated(tmp_path, ffmpeg):
    a = make(tmp_path, scores=[2, 9], n=2)
    a.run()
    assert len(a.imagegen.calls) == 3                              # 2 scenes + 1 regeneration


def test_animate_runs_per_scene_and_failure_is_tolerated(tmp_path, ffmpeg):
    anim = FakeAnimator()
    make(tmp_path, n=2, animate=True, animator=anim).run()
    assert anim.calls == 2 and len(ffmpeg) == 2 * 2 + 1
    bad = FakeAnimator(fail=True)
    ffmpeg.clear()
    make(tmp_path, n=2, animate=True, animator=bad).run()
    assert bad.calls == 2 and len(ffmpeg) == 3                     # animation skipped, video still built
