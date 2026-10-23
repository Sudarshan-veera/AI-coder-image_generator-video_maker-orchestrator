"""No agent (coding, image, video) may use a cloud AI API."""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERN = re.compile(r"google\.genai|from google import|genai\.|GEMINI|import openai|anthropic|\bveo\b", re.I)


def test_no_cloud_apis_anywhere_in_agent_code():
    for folder in ("harness", "image_agent", "video_agent", "common", ".opencode"):
        for base, dirs, names in os.walk(os.path.join(ROOT, folder)):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__")]
            for n in names:
                if n.endswith((".py", ".ts", ".md")):
                    assert not PATTERN.search(open(os.path.join(base, n)).read()), os.path.join(base, n)
    for req in ("requirements.txt", "requirements-local.txt"):
        assert not PATTERN.search(open(os.path.join(ROOT, req)).read()), req
