import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import json
import pytest
from fakes import FakeClient, text_resp, img_resp, empty_resp
import logo_agent as L


def test_parse_json_variants():
    assert L.parse_json('noise {"score": 8} tail') == {"score": 8}
    assert L.parse_json("no json") is None
    assert L.parse_json(None) is None


def test_happy_path_accepts_first_good_logo(tmp_path):
    c = FakeClient([text_resp("brand"), text_resp("logo prompt"), img_resp(),
                    text_resp('{"score": 8, "feedback": "good"}')])
    out = L.LogoAgent(client=c, team="T", outdir=str(tmp_path)).run()
    assert out and os.path.exists(out) and out.endswith("team_logo.png")
    assert len(c.models.calls) == 4


def test_retries_until_threshold(tmp_path):
    c = FakeClient([text_resp("b"), text_resp("p"),
                    img_resp(b"one"), text_resp('{"score": 3, "feedback": "too busy"}'),
                    img_resp(b"two"), text_resp('{"score": 9, "feedback": "great"}')])
    agent = L.LogoAgent(client=c, team="T", outdir=str(tmp_path))
    out = agent.run()
    assert open(out, "rb").read() == b"two"
    assert [a["score"] for a in agent.log] == [3.0, 9.0]


def test_keeps_best_when_none_reach_threshold(tmp_path):
    rs = [text_resp("b"), text_resp("p")]
    for data, sc in ((b"a", 2), (b"b", 6), (b"c", 4)):
        rs += [img_resp(data), text_resp(json.dumps({"score": sc, "feedback": "f"}))]
    out = L.LogoAgent(client=FakeClient(rs), team="T", outdir=str(tmp_path)).run()
    assert open(out, "rb").read() == b"b"


def test_returns_none_if_no_image_ever_returned(tmp_path):
    rs = [text_resp("b"), text_resp("p"), empty_resp(), empty_resp(), empty_resp()]
    assert L.LogoAgent(client=FakeClient(rs), team="T", outdir=str(tmp_path)).run() is None


def test_garbage_evaluation_scores_zero(tmp_path):
    rs = [text_resp("b"), text_resp("p"), img_resp(), text_resp("lol no json")]
    agent = L.LogoAgent(client=FakeClient(rs), team="T", outdir=str(tmp_path))
    agent.run(max_attempts=1)
    assert agent.log[0]["score"] == 0.0


def test_writes_log_file(tmp_path):
    rs = [text_resp("b"), text_resp("p"), img_resp(), text_resp('{"score": 9}')]
    L.LogoAgent(client=FakeClient(rs), team="T", outdir=str(tmp_path)).run()
    assert "attempts" in json.load(open(tmp_path / "logo_agent_log.json"))
