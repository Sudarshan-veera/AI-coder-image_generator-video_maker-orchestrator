"""Tiny orchestration engine shared by the three agents.

An agent is an Orchestrator that runs independent Tasks over a shared context dict.
Each task reads what it needs from ctx and returns a dict of updates.
"""
import json, os, time


class TaskError(RuntimeError):
    pass


class Task:
    def __init__(self, name, fn, retries=0, optional=False, when=None, description=""):
        self.name = name
        self.fn = fn
        self.retries = retries        # extra attempts after the first failure
        self.optional = optional      # failure is recorded but does not stop the agent
        self.when = when              # callable(ctx) -> bool; task is skipped if False
        self.description = description


class Orchestrator:
    def __init__(self, agent, trace_path=None):
        self.agent = agent
        self.trace_path = trace_path
        self.events = []

    def _event(self, task, status, seconds, ctx, attempt=1, error=""):
        self.events.append({"agent": self.agent, "task": task, "status": status,
                            "seconds": round(seconds, 2), "round": ctx.get("round"),
                            "attempt": attempt, "error": str(error)[:200]})

    def run_task(self, task, ctx):
        if task.when and not task.when(ctx):
            self._event(task.name, "skipped", 0, ctx)
            return
        last = None
        for attempt in range(1, task.retries + 2):
            t0 = time.time()
            try:
                update = task.fn(ctx)
                if update:
                    ctx.update(update)
                self._event(task.name, "ok", time.time() - t0, ctx, attempt)
                return
            except Exception as e:                      # noqa: BLE001
                last = e
                self._event(task.name, "failed", time.time() - t0, ctx, attempt, e)
        if task.optional:
            return
        raise TaskError(f"{self.agent}.{task.name} failed: {last}") from last

    def run(self, tasks, ctx):
        for t in tasks:
            self.run_task(t, ctx)
        return ctx

    def loop(self, tasks, ctx, done, max_rounds=3):
        for rnd in range(1, max_rounds + 1):
            ctx["round"] = rnd
            self.run(tasks, ctx)
            if done(ctx):
                break
        return ctx

    def save(self, path=None):
        path = path or self.trace_path
        if not path:
            return None
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2)
        return path
