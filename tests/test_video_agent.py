import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import json
import pytest
from fakes import FakeClient, text_resp, img_resp
import video_agent as V

SCENES = {"scenes": [
    {"subject": "A user", "action": "types a category", "scene": "desk", "style": "flat",
     "camera": "close-up", "dialogue": "Enter a category.", "sound_effects": "typing"},
    {"subject": "Agents", "action": "search the web", "scene": "network", "style": "flat",
     "camera": "pan", "dialogue": "Agents research.", "sound_effects": "whoosh"}]}


def test_plan_scenes_parses_and_limits(tmp_path):
    c = FakeClient([text_resp(json.dumps(SCENES))])
    out = V.VideoAgent(client=c, outdir=str(tmp_path), n_scenes=1).plan_scenes()
    assert len(out) == 1 and out[0]["subject"] == "A user"


def test_plan_scenes_raises_on_garbage(tmp_path):
    c = FakeClient([text_resp("nothing useful")])
    with pytest.raises(RuntimeError):
        V.VideoAgent(client=c, outdir=str(tmp_path)).plan_scenes()


def test_scene_prompt_contains_all_parts_and_tolerates_missing_keys():
    p = V.VideoAgent.scene_prompt(SCENES["scenes"][0])
    for word in ("A user", "close-up", "Enter a category.", "typing"):
        assert word in p
    assert isinstance(V.VideoAgent.scene_prompt({}), str)


def test_evaluate_scene_parses_number(tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(b"x")
    a = V.VideoAgent(client=FakeClient([text_resp("Score: 8.5")]), outdir=str(tmp_path))
    assert a.evaluate_scene(SCENES["scenes"][0], str(img)) == 8.5
    a = V.VideoAgent(client=FakeClient([text_resp("no idea")]), outdir=str(tmp_path))
    assert a.evaluate_scene(SCENES["scenes"][0], str(img)) == 0.0


def test_full_run_with_veo_stitches_clips(tmp_path, monkeypatch):
    rs = [text_resp(json.dumps(SCENES))]
    for _ in SCENES["scenes"]:
        rs += [img_resp(), text_resp("9")]
    calls = []
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, check: calls.append(cmd))
    a = V.VideoAgent(client=FakeClient(rs), outdir=str(tmp_path), n_scenes=2, poll=0)
    out = a.run()
    assert out.endswith("how_it_works.mp4")
    assert (tmp_path / "scenes" / "scene1.mp4").exists() and (tmp_path / "scenes" / "scene2.mp4").exists()
    assert calls and calls[0][0] == "ffmpeg" and "concat" in calls[0]
    assert (tmp_path / "video_plan.json").exists()


def test_weak_frame_is_regenerated_once(tmp_path, monkeypatch):
    rs = [text_resp(json.dumps({"scenes": [SCENES["scenes"][0]]})),
          img_resp(), text_resp("2"), img_resp()]          # weak score -> second image
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, check: None)
    c = FakeClient(rs)
    V.VideoAgent(client=c, outdir=str(tmp_path), n_scenes=1, poll=0).run()
    assert c.models.responses == []                          # all queued responses consumed


def test_slideshow_mode_skips_veo(tmp_path, monkeypatch):
    rs = [text_resp(json.dumps(SCENES))]
    for _ in SCENES["scenes"]:
        rs += [img_resp(), text_resp("9")]
    calls = []
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, check: calls.append(cmd))
    c = FakeClient(rs)
    V.VideoAgent(client=c, outdir=str(tmp_path), n_scenes=2).run(slideshow=True)
    assert not (tmp_path / "scenes" / "scene1.mp4").exists()
    assert any("scale=1280:720,format=yuv420p" in part for part in calls[0])
