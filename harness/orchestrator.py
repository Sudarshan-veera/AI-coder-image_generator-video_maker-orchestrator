"""Coding agent orchestrator: independent tasks over a shared context, local LLM only."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.orchestrator import Orchestrator, Task
import agents as A

MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "3"))


def build_tasks():
    def plan(ctx):
        return {"queries": A.planner(ctx["category"], ctx["round"])}

    def research(ctx):
        return {"docs": A.researcher(ctx["queries"])}

    def extract(ctx):
        found = A.extractor(ctx["category"], ctx["docs"])
        return {"candidates": A.merge_candidates(ctx["candidates"] + found)}

    def filt(ctx):
        return {"pool": A.filter_startups(ctx["candidates"])}

    def rank(ctx):
        return {"top": A.ranker(ctx["category"], ctx["pool"])[:10]}

    def enrich(ctx):
        return {"top": A.enricher(ctx["category"], ctx["top"])}

    def critic(ctx):
        return {"issues": A.critic(ctx["top"])}

    return [
        Task("plan", plan, retries=1, description="category -> search queries"),
        Task("research", research, description="web + news search, page fetch"),
        Task("extract", extract, description="LLM extracts startup facts, merges duplicates"),
        Task("filter", filt, description="drop public/acquired companies"),
        Task("rank", rank, description="score by valuation, funding, momentum, mentions"),
        Task("enrich", enrich, description="fill missing news / funding / valuation"),
        Task("critic", critic, description="validate; failures trigger another round"),
    ]


def run(category, outdir="outputs"):
    orch = Orchestrator("startup_agent", os.path.join(outdir, "trace.json"))
    ctx = {"category": category, "candidates": [], "top": [], "issues": []}
    try:
        orch.loop(build_tasks(), ctx, done=lambda c: not c["issues"], max_rounds=MAX_ROUNDS)
        orch.run([Task("report", lambda c: {"path": A.reporter(
            c["category"], c["top"], outdir=outdir, warnings=c["issues"])})], ctx)
    finally:
        orch.save()
        with open(os.path.join(outdir, "agent_log.json"), "w") as f:
            json.dump(A.TRACE, f, indent=2)
    print(open(ctx["path"]).read())
    return ctx


if __name__ == "__main__":
    run(" ".join(sys.argv[1:]) or "FinTech")
