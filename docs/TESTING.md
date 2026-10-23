# Testing

## Automated (offline)
`make test` runs pytest with every Ollama, search and Gemini call mocked.
| File | Covers |
|---|---|
| test_core_orchestrator.py | engine: context flow, retries, optional, when, loop, trace |
| test_tools.py / test_agents.py | search tools and each coding-agent task |
| test_orchestrator.py | coding-agent pipeline, critic retries, public-company filter |
| test_image_agent.py / test_video_agent.py / test_generate_image.py | image and video capabilities |
| test_contracts.py | each agent runs its documented tasks and writes its trace |
| test_agent_independence.py | agents do not import each other |
| test_local_only.py | coding agent and OpenCode config use only local Ollama |
| test_live.py | optional, `RUN_LIVE=1`, real model + web |

## Manual verification of real outputs
1. `make startups CATEGORY="FinTech"`, `make logo`, `make video`
2. Inspect traces with `jq` (see README), then run `make verify`
3. `opencode`, choose `scout`, type `FinTech`: the tool call `top_startups` must appear
