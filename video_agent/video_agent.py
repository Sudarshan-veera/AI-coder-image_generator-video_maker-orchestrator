"""Video agent (fully local): an orchestrator of independent tasks.
plan_scenes -> narration_polish -> per scene [art -> evaluate_frame -> regenerate_if_weak ->
compose_frame -> narrate -> render_clip -> animate_clip] -> assemble
Art: SDXL-Turbo. Check: CLIP. Voice: espeak-ng. Video: ffmpeg (+ optional LTX-Video motion).
"""
import argparse, json, os, subprocess, sys, wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.orchestrator import Orchestrator, Task
from common.local_llm import ask as default_llm
from common.local_image import LocalImageGen, compose_overlay, compose_scene

SCENES = [
    {"title": "Three independent agents",
     "tasks": ["Coding agent", "Image agent", "Video agent"],
     "art": "abstract glowing network of connected nodes, dark blue background, digital art",
     "caption": "Each agent is an orchestrator of independent tasks on one small shared engine.",
     "narration": "Our system has three independent agents. Each one is an orchestrator that runs "
                  "its own tasks, and every task is traced and tested."},
    {"title": "Coding agent: local LLM",
     "tasks": ["plan", "research", "extract", "filter", "rank", "enrich", "critic", "report"],
     "art": "futuristic data center with flowing streams of light and documents, blue and teal",
     "caption": "Runs on a local open source model with Ollama. The critic can send it back for another round.",
     "narration": "The coding agent runs on a local open source model. It plans searches, researches "
                  "the web, extracts facts, filters out public companies, ranks the rest and "
                  "enriches missing data. A critic can send it back for another round before the "
                  "final top ten report."},
    {"title": "Image agent: team logo",
     "tasks": ["brand", "concept", "generate", "evaluate", "refine", "finalize"],
     "art": "artist studio with glowing holographic design sketches, purple and blue, digital art",
     "caption": "A local diffusion model draws the emblem, CLIP scores it, and the name is added with crisp text.",
     "narration": "The image agent writes a brand brief, creates a prompt, draws an emblem with a "
                  "local diffusion model, scores it, and refines it until it passes. Then it adds "
                  "the team name."},
    {"title": "Video agent: this video",
     "tasks": ["plan", "art", "evaluate", "compose", "narrate", "render", "assemble"],
     "art": "film editing studio with glowing timeline screens, dark teal, cinematic digital art",
     "caption": "Local diffusion art, a local voice, and ffmpeg turn the plan into this video.",
     "narration": "The video agent plans scenes, draws background art, checks quality, composes the "
                  "diagram, records narration with a local voice, and assembles the clips with "
                  "ffmpeg."},
    {"title": "Everything runs locally",
     "tasks": ["Ollama LLM", "SDXL-Turbo", "CLIP", "espeak-ng", "ffmpeg"],
     "art": "single glowing laptop at night surrounded by floating light particles, digital art",
     "caption": "No cloud API is used by any agent.",
     "narration": "Everything runs on one laptop. A local language model, a local image model and "
                  "local tools, with no cloud services."},
]


class EspeakTTS:
    def speak(self, text, path):
        subprocess.run(["espeak-ng", "-v", os.getenv("TTS_VOICE", "en-us"), "-s", "150",
                        "-w", path, text], check=True)
        with wave.open(path) as w:
            return w.getnframes() / float(w.getframerate())


def trace_summary(outdir):
    try:
        ev = json.load(open(os.path.join(outdir, "trace.json")))
        ok = [e for e in ev if e.get("status") == "ok"]
        rounds = max([e.get("round") or 1 for e in ok] or [1])
        return f"Last coding-agent run: {rounds} round(s), {len(ok)} tasks, {sum(e['seconds'] for e in ok):.0f} s"
    except Exception:                                       # noqa: BLE001
        return None


class VideoAgent:
    def __init__(self, llm=None, imagegen=None, tts=None, animator=None, outdir="outputs",
                 n_scenes=5, animate=False, min_score=4.0):
        self.llm = llm or default_llm
        self.imagegen = imagegen or LocalImageGen()
        self.tts = tts or EspeakTTS()
        self.animator = animator
        self.animate = animate
        self.outdir = outdir
        self.scenes_dir = os.path.join(outdir, "scenes")
        self.n = n_scenes
        self.min_score = min_score
        self.orch = None
        os.makedirs(self.scenes_dir, exist_ok=True)

    # ---- independent capabilities -------------------------------------
    def plan_scenes(self):
        scenes = [dict(s) for s in SCENES][: self.n]
        note = trace_summary(self.outdir)
        if note and len(scenes) > 1:
            scenes[1]["note"] = note
        return scenes

    def polish_narration(self, scenes):
        for s in scenes:
            try:
                text = self.llm("Rewrite this narration for a short explainer video in friendly "
                                "plain English, 25 to 45 words, keep every technical term. Reply "
                                "with only the narration.\n\n" + s["narration"])
            except Exception:                               # noqa: BLE001
                continue
            if text and 15 <= len(text.split()) <= 70 and not text.startswith("{"):
                s["narration"] = " ".join(text.split())
        return scenes

    def _ffmpeg(self, args):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args, check=True)

    # ---- orchestration -------------------------------------------------
    def scene_tasks(self):
        def p(ctx, name):
            return os.path.join(self.scenes_dir, f"scene{ctx['i']}_{name}")

        def t_art(ctx):
            path = p(ctx, "art.png")
            self.imagegen.generate(ctx["scene"]["art"], path, width=768, height=432, seed=100 * ctx["i"])
            return {"art": path}

        def t_eval(ctx):
            return {"score": float(self.imagegen.score(ctx["art"], ctx["scene"]["art"]))}

        def t_regen(ctx):
            self.imagegen.generate(ctx["scene"]["art"], ctx["art"], width=768, height=432,
                                   seed=100 * ctx["i"] + 1)

        def t_compose(ctx):
            s = ctx["scene"]
            overlay, frame = p(ctx, "overlay.png"), p(ctx, "frame.png")
            compose_overlay(s["title"], s["tasks"], s["caption"], overlay, note=s.get("note"))
            compose_scene(ctx["art"], overlay, frame)
            return {"overlay": overlay, "frame": frame}

        def t_narrate(ctx):
            wav = p(ctx, "voice.wav")
            return {"wav": wav, "dur": self.tts.speak(ctx["scene"]["narration"], wav)}

        def t_render(ctx):
            clip = p(ctx, "clip.mp4")
            frames = int((ctx["dur"] + 0.5) * 25)
            vf = ("scale=2560:1440,zoompan=z='min(zoom+0.0006,1.12)':d=%d:x='iw/2-(iw/zoom/2)':"
                  "y='ih/2-(ih/zoom/2)':s=1280x720:fps=25,format=yuv420p" % frames)
            self._ffmpeg(["-i", ctx["frame"], "-i", ctx["wav"], "-vf", vf, "-af", "apad",
                          "-t", f"{ctx['dur'] + 0.5:.2f}", "-c:v", "libx264", "-c:a", "aac",
                          "-ar", "44100", clip])
            ctx["clips"].append(clip)
            return {"clip": clip}

        def t_animate(ctx):
            if self.animator is None:
                from animator import LTXAnimator
                self.animator = LTXAnimator()
            anim = p(ctx, "anim.mp4")
            self.animator.animate(ctx["art"], ctx["scene"]["art"], anim)
            self._ffmpeg(["-stream_loop", "-1", "-i", anim, "-i", ctx["overlay"], "-i", ctx["wav"],
                          "-filter_complex",
                          "[0:v]scale=1280:720,setsar=1[bg];[bg][1:v]overlay=0:0,format=yuv420p[v]",
                          "-map", "[v]", "-map", "2:a", "-af", "apad", "-r", "25",
                          "-t", f"{ctx['dur'] + 0.5:.2f}", "-c:v", "libx264", "-c:a", "aac",
                          "-ar", "44100", ctx["clip"]])

        return [Task("art", t_art, retries=1),
                Task("evaluate_frame", t_eval),
                Task("regenerate_if_weak", t_regen, when=lambda c: c.get("score", 10) < self.min_score),
                Task("compose_frame", t_compose),
                Task("narrate", t_narrate, retries=1),
                Task("render_clip", t_render),
                Task("animate_clip", t_animate, optional=True, when=lambda c: self.animate)]

    def run(self):
        out = os.path.join(self.outdir, "how_it_works.mp4")
        self.orch = Orchestrator("video_agent", os.path.join(self.outdir, "video_agent_trace.json"))
        ctx = {"clips": []}

        def t_plan(c):
            return {"scenes": self.plan_scenes()}

        def t_polish(c):
            return {"scenes": self.polish_narration(c["scenes"])}

        def t_assemble(c):
            with open(os.path.join(self.outdir, "video_plan.json"), "w") as f:
                json.dump(c["scenes"], f, indent=2)
            lst = os.path.join(self.scenes_dir, "list.txt")
            with open(lst, "w") as f:
                for clip in c["clips"]:
                    f.write(f"file '{os.path.abspath(clip)}'\n")
            self._ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
            return {"out": out}

        try:
            self.orch.run([Task("plan_scenes", t_plan),
                           Task("narration_polish", t_polish, optional=True)], ctx)
            for i, s in enumerate(ctx["scenes"], 1):
                ctx.update({"i": i, "scene": s, "round": i, "score": 10})
                self.orch.run(self.scene_tasks(), ctx)
            self.orch.run([Task("assemble", t_assemble)], ctx)
        finally:
            self.orch.save()
            for backend in (self.imagegen, self.animator):
                if backend is not None and hasattr(backend, "unload"):
                    backend.unload()
        return ctx["out"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the 'how it works' video with local models.")
    ap.add_argument("--scenes", type=int, default=5)
    ap.add_argument("--animate", action="store_true", help="experimental: add LTX-Video motion")
    ap.add_argument("--outdir", default="outputs")
    a = ap.parse_args()
    print("video ->", VideoAgent(outdir=a.outdir, n_scenes=a.scenes, animate=a.animate).run())
