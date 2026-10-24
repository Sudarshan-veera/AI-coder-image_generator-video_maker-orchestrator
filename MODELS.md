# Models, APIs and Tools

## Coding agent (local only, no cloud LLM)
- Model: Qwen3.5 9B (qwen3.5:9b), open source, run locally via Ollama
- Custom Modelfile: `agent-coder` (num_ctx 16384, temperature 0.2)
- Harness: OpenCode agent `scout` plus a Python pipeline (plan, research, extract, filter, rank, enrich, critic, report)
- Search: DuckDuckGo (no API key)
- Local-only rule enforced by tests/test_local_only.py

## Image agent (API)
- Gemini text model (gemini-2.5-flash) for brand analysis and concepts
- Gemini image model (gemini-2.5-flash-image) for logo generation and evaluation

## Video agent (API)
- Gemini text model for scene planning and narration
- Veo (veo-3.0-fast-generate-001) for video clips
- ffmpeg for assembly (slideshow fallback)

## Orchestration
- Custom lightweight task orchestrator (common/orchestrator.py), pure Python, no framework.
- Every agent writes a task trace (status, retries, timings).

## Other tools
- Python 3, pytest, Make, GitHub Actions (tests), WSL Ubuntu 24.04
