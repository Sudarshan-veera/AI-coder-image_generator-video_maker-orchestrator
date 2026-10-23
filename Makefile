.RECIPEPREFIX := >
CATEGORY ?= FinTech

test:
> pytest -q

startups:
> python harness/orchestrator.py "$(CATEGORY)"

free-gpu:
> ollama stop agent-coder || true

logo: free-gpu
> python image_agent/logo_agent.py

video: free-gpu
> python video_agent/video_agent.py

all: startups logo video

verify:
> python scripts/verify_outputs.py

e2e: test all verify

examples:
> mkdir -p examples/images
> cp outputs/team_logo.png examples/images/
> cp outputs/scenes/scene*_frame.png examples/images/ 2>/dev/null || true
> cp outputs/*_top10.md examples/
> cp outputs/trace.json examples/startup_agent_trace.json
> cp outputs/image_agent_trace.json outputs/video_agent_trace.json examples/
> test -f outputs/how_it_works.mp4 && cp outputs/how_it_works.mp4 examples/ || true
> ls -lh examples examples/images

zip:
> cd .. && rm -f startup-agents-harness.zip && zip -r startup-agents-harness.zip startup-agents -x "startup-agents/.venv/*" "startup-agents/outputs/*" "startup-agents/examples/*" "startup-agents/.git/*" "*/__pycache__/*" "*/.pytest_cache/*" "*/node_modules/*"
