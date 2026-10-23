import { tool } from "@opencode-ai/plugin"

export default tool({
  description:
    "Research and rank the top 10 best-performing startups for a category (e.g. FinTech). " +
    "Runs the local multi-agent harness (planner, researcher, extractor, ranker, critic, reporter). " +
    "Takes a few minutes. Returns a Markdown table with sources.",
  args: {
    category: tool.schema.string().describe("Startup category, e.g. FinTech, HealthTech, AgriTech"),
  },
  async execute(args, context) {
    const root = context.worktree
    const out = await Bun
      .$`${root}/.venv/bin/python ${root}/harness/orchestrator.py ${args.category}`
      .cwd(root)
      .text()
    return out.slice(-12000)
  },
})
