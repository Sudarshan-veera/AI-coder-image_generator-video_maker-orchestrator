"""Image agent (fully local): an orchestrator of independent tasks."""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.orchestrator import Orchestrator, Task
from common.local_llm import ask as default_llm
from common.local_image import LocalImageGen, make_logo

SUFFIX = (", logo emblem, flat vector style, bold simple shapes, centered, plain white "
          "background, no text, no letters, no words")
MODIFIERS = ["symmetrical, minimal, high contrast",
             "geometric, clean lines, vibrant colors",
             "simple icon, bold silhouette"]

class LogoAgent:
    def __init__(self, llm=None, imagegen=None, team=None, outdir="outputs", seed=7):
        self.llm = llm or default_llm
        self.imagegen = imagegen or LocalImageGen()
        self.team = team or os.getenv("TEAM_NAME", "Startup Scout")
        self.outdir = outdir
        self.seed = seed
        self.fallbacks = []
        self.last = {"best": (0, "")}
        self.log = []
        self.orch = Orchestrator("image_agent", os.path.join(self.outdir, "image_agent_trace.json"))

    def run(self):
        os.makedirs(self.outdir, exist_ok=True)
        ctx = {"team": self.team, "seed": self.seed, "best_score": 0, "best_img": "", "attempt": 0}
        
        def t_brand(c): 
            self.fallbacks.append("brand_analysis")
            return {"concept": "a glowing hexagon of nodes"}
            
        def t_concepts(c): 
            self.fallbacks.append("design_concepts")
            return {"prompt": c["concept"] + SUFFIX}
            
        def t_refine(c):
            mod = MODIFIERS[c["attempt"] % len(MODIFIERS)]
            return {"prompt": c["concept"] + ", " + mod + SUFFIX}

        def t_generate(c):
            c["attempt"] += 1
            img = os.path.join(self.outdir, f"v{c['attempt']}.png")
            self.imagegen.generate(c["prompt"], img, 1024, 1024, seed=c["seed"] + c["attempt"])
            return {"current_img": img}

        def t_eval(c):
            score = self.imagegen.score(c["current_img"], c["prompt"])
            self.log.append({"score": score})
            if score > c["best_score"]:
                c["best_score"] = score
                c["best_img"] = c["current_img"]
                self.last["best"] = (score, c["current_img"])
            if score < 7.0:
                raise ValueError(f"Score {score} too low")
            return {"passed": True}

        def t_finalize(c):
            team_final = os.path.join(self.outdir, "team_logo.png")
            make_logo(c["best_img"], self.team, team_final)
            return {"final": team_final}

        try:
            self.orch.run([
                Task("brand_analysis", t_brand),
                Task("design_concepts", t_concepts),
                Task("generate_and_eval", lambda c: self.orch.run([
                    Task("refine", t_refine, when=lambda c: c["attempt"] > 0),
                    Task("generate", t_generate),
                    Task("evaluate", t_eval)
                ], c), retries=2),
                Task("finalize", t_finalize)
            ], ctx)
        except Exception:
            if self.last["best"][1]:
                ctx["best_img"] = self.last["best"][1]
                t_finalize(ctx)

        self.orch.save()
        with open(os.path.join(self.outdir, "logo_agent_log.json"), "w") as f:
            json.dump({"attempts": self.orch.events}, f)

        return ctx.get("final", os.path.join(self.outdir, "team_logo.png"))

if __name__ == "__main__":
    print("logo ->", LogoAgent().run())
