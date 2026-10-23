# Tech Stack
- Python 3.12, venv at .venv
- LLM: Ollama, model agent-coder (qwen3.5:9b, 32k ctx); override with AGENT_MODEL
- Search: ddgs (DuckDuckGo), page text: trafilatura
- Orchestration: plain Python, one function per agent, shared trace log
- CLI: python harness/orchestrator.py "<category>"
