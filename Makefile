.RECIPEPREFIX := >
CATEGORY ?= FinTech

test:
> pytest -q

startups:
> python harness/orchestrator.py "$(CATEGORY)"

logo:
> python image_agent/logo_agent.py

video:
> python video_agent/video_agent.py --slideshow

all: startups logo video

verify:
> python scripts/verify_outputs.py

zip:
> cd .. && rm -f startup-agents-harness.zip && zip -r startup-agents-harness.zip startup-agents -x "startup-agents/.venv/*" "startup-agents/outputs/*" "startup-agents/examples/*" "startup-agents/.git/*" "*/__pycache__/*" "*/.pytest_cache/*" "*/node_modules/*"
