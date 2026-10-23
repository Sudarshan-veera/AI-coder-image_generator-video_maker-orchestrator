
## Orchestration model (current)
Each agent is an `Orchestrator` (common/orchestrator.py) running independent `Task`s over a shared
context dict, with retries, optional tasks, conditional tasks (`when`), loops with a stop condition
and a JSON trace. The coding agent loops plan..critic; the image agent loops generate..refine; the
video agent runs one task chain per scene. Task lists are documented in docs/AGENTS.md and enforced
by tests/test_contracts.py.
