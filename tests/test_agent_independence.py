"""The three agents share only common/ and never import each other's modules."""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = {
    "harness": ["logo_agent", "video_agent", "image_agent", "google"],
    "image_agent": ["video_agent", "agents", "orchestrator", "tools", "ollama"],
    "video_agent": ["logo_agent", "image_agent", "agents", "orchestrator", "tools", "ollama"],
}


def imported(folder):
    names = set()
    for n in os.listdir(os.path.join(ROOT, folder)):
        if n.endswith(".py"):
            for line in open(os.path.join(ROOT, folder, n)):
                m = re.match(r"\s*(?:from|import)\s+([A-Za-z_][\w]*)", line)
                if m:
                    names.add(m.group(1))
    return names


def test_agents_do_not_import_each_other():
    for folder, forbidden in RULES.items():
        bad = imported(folder) & set(forbidden)
        # a module may import its own sibling files (e.g. harness importing agents/tools)
        bad -= {f for f in bad if folder == "harness" and f in ("agents", "tools")}
        assert not bad, f"{folder} imports {bad}"


def test_all_agents_use_the_shared_engine():
    for folder, mod in (("harness", "orchestrator.py"), ("image_agent", "logo_agent.py"),
                        ("video_agent", "video_agent.py")):
        assert "from common.orchestrator import" in open(os.path.join(ROOT, folder, mod)).read()
