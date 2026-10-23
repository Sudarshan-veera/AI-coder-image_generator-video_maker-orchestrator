"""Image agent: an orchestrator of independent tasks.
brand_analysis -> design_concepts -> [generate -> evaluate -> refine] x N -> finalize
"""
import argparse, json, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.orchestrator import Orchestrator, Task


def get_client():
    from google import genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _png_part(path):
    from google.genai import types
    with open(path, "rb") as f:
        return types.Part.from_bytes(data=f.read(), mime_type="image/png")


class LogoAgent:
    def __init__(self, client=None, team=None, ref=None, outdir="outputs"):
        self.client = client or get_client()
        self.team = team or os.getenv("TEAM_NAME", "Startup Scout")
        self.ref = ref
        self.outdir = outdir
        self.text_model = os.getenv("TEXT_MODEL", "gemini-2.5-flash")
        self.image_model = os.getenv("IMAGE_MODEL", "gemini-2.5-flash-image")
        self.log = []
        self.orch = None

    # ---- independent capabilities -------------------------------------
    def _ask(self, prompt, parts=None):
        r = self.client.models.generate_content(
            model=self.text_model, contents=(parts or []) + [prompt])
        return r.text

    def brand_analysis(self):
        parts = [_png_part(self.ref)] if self.ref else []
        return self._ask(
            f"Define a brand identity (values, personality, palette, shapes, typography mood) "
            f"for a student team called '{self.team}' building a multi-agent system that "
            f"researches the best startups. Under 150 words.", parts)

    def design_concepts(self, brand):
        return self._ask(
            "Using this brand analysis, write ONE image-generation prompt for a logo with these "
            "attributes: Subject, Action, Location (background), Composition, Style. Flat vector "
            f"logo, centered, plain background, no tiny text. Include the text '{self.team}'. "
            "Reply with only the prompt.\n\n" + str(brand))

    def generate(self, prompt, path):
        contents = [prompt]
        if self.ref:
            contents.insert(0, _png_part(self.ref))
        r = self.client.models.generate_content(model=self.image_model, contents=contents)
        for cand in (r.candidates or []):
            for p in cand.content.parts:
                if getattr(p, "inline_data", None):
                    with open(path, "wb") as f:
                        f.write(p.inline_data.data)
                    return True
        return False

    def evaluate(self, path):
        out = self._ask(
            "Score this logo 1-10 on legibility, simplicity, memorability, brand fit. "
            'Reply JSON only: {"score": n, "feedback": "..."}', [_png_part(path)])
        ev = parse_json(out) or {"score": 0, "feedback": out}
        try:
            ev["score"] = float(ev.get("score", 0))
        except (TypeError, ValueError):
            ev["score"] = 0.0
        return ev

    # ---- orchestration -------------------------------------------------
    def build_tasks(self, threshold):
        def t_brand(ctx):
            return {"brand": self.brand_analysis()}

        def t_concept(ctx):
            return {"prompt": self.design_concepts(ctx["brand"])}

        def t_generate(ctx):
            n = ctx["round"]
            path = os.path.join(self.outdir, f"team_logo_v{n}.png")
            ok = self.generate(ctx["prompt"], path)
            if not ok:
                self.log.append({"attempt": n, "error": "no image returned"})
            return {"path": path, "image_ok": ok, "accepted": False}

        def t_evaluate(ctx):
            ev = self.evaluate(ctx["path"])
            self.log.append({"attempt": ctx["round"], "score": ev["score"],
                             "feedback": ev.get("feedback")})
            best = ctx["best"]
            if ev["score"] > best[0]:
                best = (ev["score"], ctx["path"])
            return {"score": ev["score"], "feedback": ev.get("feedback"),
                    "accepted": ev["score"] >= threshold, "best": best}

        def t_refine(ctx):
            return {"prompt": ctx["prompt"] + "\nImprove based on this feedback: "
                    + str(ctx.get("feedback"))}

        def t_finalize(ctx):
            with open(os.path.join(self.outdir, "logo_agent_log.json"), "w") as f:
                json.dump({"brand": ctx.get("brand"), "prompt": ctx.get("prompt"),
                           "attempts": self.log}, f, indent=2)
            path = ctx["best"][1]
            if not path:
                return {"final": None}
            final = os.path.join(self.outdir, "team_logo.png")
            shutil.copy(path, final)
            return {"final": final}

        setup = [Task("brand_analysis", t_brand, retries=1),
                 Task("design_concepts", t_concept, retries=1)]
        attempt = [Task("generate", t_generate, retries=1),
                   Task("evaluate", t_evaluate, when=lambda c: c.get("image_ok")),
                   Task("refine", t_refine,
                        when=lambda c: c.get("image_ok") and not c.get("accepted"))]
        finish = [Task("finalize", t_finalize)]
        return setup, attempt, finish

    def run(self, max_attempts=3, threshold=7):
        os.makedirs(self.outdir, exist_ok=True)
        self.orch = Orchestrator("image_agent", os.path.join(self.outdir, "image_agent_trace.json"))
        ctx = {"best": (-1, None), "accepted": False, "final": None}
        setup, attempt, finish = self.build_tasks(threshold)
        try:
            self.orch.run(setup, ctx)
            self.orch.loop(attempt, ctx, lambda c: c["accepted"], max_attempts)
            self.orch.run(finish, ctx)
        finally:
            self.orch.save()
        return ctx["final"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the team logo with Gemini.")
    ap.add_argument("--ref", help="optional reference image (PNG)")
    ap.add_argument("--team", help="team name (default: $TEAM_NAME)")
    ap.add_argument("--outdir", default="outputs")
    a = ap.parse_args()
    print("logo ->", LogoAgent(team=a.team, ref=a.ref, outdir=a.outdir).run())
