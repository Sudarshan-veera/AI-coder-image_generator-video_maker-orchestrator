# Models, APIs and Tools

**No cloud LLM or cloud API is used by any agent.** Everything runs locally on one machine
(WSL Ubuntu 24.04). `tests/test_local_only.py` and `tests/test_no_cloud_apis.py` enforce this.

## Coding agent (local open-source LLM)
- Model: Qwen3.5 9B (`qwen3.5:9b`), open source, served locally by Ollama
- Custom Modelfile `agent-coder` (num_ctx 32768, temperature 0.2)
- Front end: OpenCode agent `scout` (+ `top_startups` tool); also runnable as `make startups CATEGORY=...`
- Web research: DuckDuckGo search (`ddgs`, no API key) and `trafilatura` page text extraction

## Image agent (local)
- Image model: SDXL-Turbo (`stabilityai/sdxl-turbo`) through Hugging Face `diffusers`
- Prompting / brand brief: the same local Ollama LLM
- Scoring / evaluation: CLIP (`openai/clip-vit-base-patch32`)
- Text and compositing: Pillow

## Video agent (local)
- Scene planning and narration text: local Ollama LLM
- Scene art: SDXL-Turbo; frame check: CLIP
- Voice: espeak-ng (local text-to-speech)
- Optional image-to-video motion: LTX-Video (`Lightricks/LTX-Video`) via diffusers
- Assembly: ffmpeg

## Orchestration
- Custom lightweight task orchestrator (`common/orchestrator.py`), pure Python, no framework.
  Tasks have retries, optional/conditional execution, a shared context and a saved trace
  (status, attempts, seconds) for every agent.

## Other tools
- Python 3, pytest, Make, GitHub Actions (CI tests), WSL Ubuntu 24.04
