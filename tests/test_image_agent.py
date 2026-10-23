import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from fakes import FakeImageGen, fake_llm
import logo_agent as L


def agent(tmp_path, scores=None, llm=None):
    return L.LogoAgent(llm=llm or fake_llm("a glowing hexagon of nodes"),
                       imagegen=FakeImageGen(scores), team="Test Team", outdir=str(tmp_path))


def test_happy_path_makes_1024_logo(tmp_path):
    a = agent(tmp_path, [8])
    out = a.run()
    assert out.endswith("team_logo.png") and Image.open(out).size == (1024, 1024)
    assert [e["score"] for e in a.log] == [8]


def test_emblem_prompt_forbids_text(tmp_path):
    a = agent(tmp_path, [9])
    a.run()
    prompt = a.imagegen.calls[0][0]
    assert "no text" in prompt and "hexagon" in prompt


def test_retries_with_new_seed_and_refined_prompt(tmp_path):
    a = agent(tmp_path, [3, 9])
    a.run()
    (p1, s1), (p2, s2) = a.imagegen.calls
    assert s1 != s2 and p1 != p2 and [e["score"] for e in a.log] == [3, 9]


def test_keeps_best_attempt_when_none_pass(tmp_path):
    a = agent(tmp_path, [2, 6, 4])
    a.run()
    assert len(a.imagegen.calls) == 3 and a.last["best"][1].endswith("v2.png")


def test_logo_still_made_when_llm_is_down(tmp_path):
    def down(prompt, **kw):
        raise ConnectionError("ollama down")
    a = agent(tmp_path, [9], llm=down)
    assert a.run() is not None
    assert a.fallbacks == ["brand_analysis", "design_concepts"]


def test_log_file_written(tmp_path):
    agent(tmp_path, [9]).run()
    assert "attempts" in json.load(open(tmp_path / "logo_agent_log.json"))
