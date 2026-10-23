# Startup Scout

## Mission
A multi-agent system that takes a category (e.g. "FinTech") and returns the
top 10 best-performing startups with relevant details and the latest news.
The coding agent runs on a LOCAL open-source LLM (Ollama). No cloud LLM APIs.

## Agents
- planner: turns the category into search queries
- researcher: web + news search, page fetch
- extractor: pulls startup facts out of raw text
- ranker: scores candidates on funding, growth, recency, evidence
- critic: validates the list, triggers another research round if needed
- reporter: writes Markdown + JSON

## Outputs
outputs/<category>_top10.md, outputs/<category>_top10.json, outputs/trace.json
