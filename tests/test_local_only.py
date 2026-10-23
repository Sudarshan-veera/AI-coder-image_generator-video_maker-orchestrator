"""The coding agent (harness + OpenCode config) must use only a local open-source LLM."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN = re.compile(r"google\.genai|from google import genai|genai\.Client|GEMINI_API_KEY|"
                       r"import openai|openai\.com|anthropic|ANTHROPIC_API_KEY|OPENAI_API_KEY",
                       re.I)


def _files(*dirs):
    for d in dirs:
        for base, _, names in os.walk(os.path.join(ROOT, d)):
            if "__pycache__" in base or "node_modules" in base:
                continue
            for n in names:
                if n.endswith((".py", ".ts", ".md", ".json")):
                    yield os.path.join(base, n)


def test_harness_has_no_cloud_llm_references():
    for path in _files("harness", ".opencode"):
        assert not FORBIDDEN.search(open(path).read()), f"cloud LLM reference in {path}"


def test_opencode_uses_only_local_ollama():
    cfg = json.load(open(os.path.join(ROOT, "opencode.json")))
    assert list(cfg["provider"].keys()) == ["ollama"]
    assert cfg["model"].startswith("ollama/")
    base = cfg["provider"]["ollama"]["options"]["baseURL"]
    assert re.match(r"http://(localhost|127\.0\.0\.1|10\.|192\.168\.|172\.)", base)


def test_opencode_tool_agent_and_command_exist():
    for rel in (".opencode/tool/top_startups.ts", ".opencode/agent/scout.md",
                ".opencode/command/top10.md"):
        assert os.path.exists(os.path.join(ROOT, rel)), rel
