# Agents and their tasks

All agents are orchestrators built on `common/orchestrator.py`: each **Task** reads from a shared
context, returns updates, and can have retries, be optional, or run only `when` a condition holds.
Every run records a trace (task, status, attempt, seconds).

## 1. Coding agent (local LLM, `harness/`)
| Task | What it does | LLM |
|---|---|---|
| plan | category -> search queries (fallbacks if LLM output is invalid) | yes |
| research | web + news search, de-duplicate, fetch page text | no |
| extract | pull structured facts per document, merge duplicates | yes |
| filter | drop public and acquired companies | no |
| rank | composite score: valuation 40%, funding 20%, LLM momentum 25%, mentions 15% | yes |
| enrich | fill missing latest news, funding, valuation for the top 10 | yes |
| critic | require 10 rows, sources, news, figures, not public, funding != valuation | no |
| report | Markdown table, JSON, sources, data-quality warnings | no |

Rounds repeat plan..critic until the critic is satisfied or `MAX_ROUNDS` is reached.
Front end: OpenCode agent `scout` calls the `top_startups` tool, which runs this orchestrator.
No cloud LLM API is used.

## 2. Image agent (`image_agent/logo_agent.py`, fully local)
brand_analysis -> design_concepts -> loop[ generate -> evaluate -> refine ] -> finalize.
SDXL-Turbo draws the emblem, CLIP scores it, the loop stops when the score passes or attempts run
out, and the best attempt is kept as `team_logo.png` with the team name added by Pillow.

## 3. Video agent (`video_agent/video_agent.py`, fully local)
plan_scenes, then for each scene: art (SDXL-Turbo) -> evaluate_frame -> compose overlay ->
narrate (espeak-ng) -> render clip, then assemble with ffmpeg. Optional LTX-Video adds motion.

## Independence
The agents share only `common/`. `tests/test_agent_independence.py` fails if one agent imports
another agent's modules.
