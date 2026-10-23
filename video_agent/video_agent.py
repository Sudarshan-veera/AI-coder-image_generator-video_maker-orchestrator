"""Video agent: an orchestrator of independent tasks.
plan_scenes -> per scene [scene_image -> evaluate_frame -> regenerate_if_weak -> collect_frame
-> scene_video] -> assemble
"""
import argparse, json, os, re, subprocess, sys, time

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


def _read(path, limit=3000):
    return open(path).read()[:limit] if os.path.exists(path) else ""


class VideoAgent:
    def __init__(self, client=None, outdir="outputs", n_scenes=4, poll=10):
        self.client = client or get_client()
        self.outdir = outdir
        self.scenes_dir = os.path.join(outdir, "scenes")
        self.n = n_scenes
        self.poll = poll
        self.text_model = os.getenv("TEXT_MODEL", "gemini-2.5-flash")
        self.image_model = os.getenv("IMAGE_MODEL", "gemini-2.5-flash-image")
        self.video_model = os.getenv("VIDEO_MODEL", "veo-3.0-fast-generate-001")
        self.orch = None
        os.makedirs(self.scenes_dir, exist_ok=True)

    # ---- independent capabilities -------------------------------------
    def plan_scenes(self):
        spec = _read("specs/mission.md")
        trace = _read(os.path.join(self.outdir, "trace.json"))
        r = self.client.models.generate_content(model=self.text_model, contents=[
            f"Plan a {self.n}-scene explainer video (8 seconds each) showing how this system "
            "works: three independent agents, each an orchestrator of tasks. (1) Coding agent on "
            "a local open-source LLM: plan, research, extract, filter, rank, enrich, critic loop, "
            "report -> top-10 startups. (2) Image agent: brand analysis, design concepts, "
            "generate, evaluate, refine -> team logo. (3) Video agent: plan scenes, scene images, "
            "Veo animation, assemble. For each scene give keys: subject, action, scene, style, "
            "camera, dialogue (one short narration line), sound_effects. "
            'Reply JSON only: {"scenes": [...]}\n\nSPEC:\n' + spec + "\nTRACE:\n" + trace])
        scenes = (parse_json(r.text) or {}).get("scenes") or []
        if not scenes:
            raise RuntimeError("scene planner returned no scenes")
        return scenes[: self.n]

    @staticmethod
    def scene_prompt(s):
        g = lambda k: s.get(k, "")
        return (f"{g('subject')} {g('action')}. Scene: {g('scene')}. Style: {g('style')}. "
                f"Camera: {g('camera')}. Narrator says: \"{g('dialogue')}\". "
                f"Sound: {g('sound_effects')}.")

    def scene_image(self, s, i):
        r = self.client.models.generate_content(model=self.image_model, contents=[
            "Clean reference diagram frame, 16:9, flat infographic style: " + self.scene_prompt(s)])
        for cand in (r.candidates or []):
            for p in cand.content.parts:
                if getattr(p, "inline_data", None):
                    path = os.path.join(self.scenes_dir, f"scene{i}.png")
                    with open(path, "wb") as f:
                        f.write(p.inline_data.data)
                    return path
        raise RuntimeError(f"scene {i}: no reference image returned")

    def scene_video(self, s, i, img):
        from google.genai import types
        with open(img, "rb") as f:
            image = types.Image(image_bytes=f.read(), mime_type="image/png")
        op = self.client.models.generate_videos(
            model=self.video_model, prompt=self.scene_prompt(s), image=image,
            config=types.GenerateVideosConfig(aspect_ratio="16:9"))
        while not op.done:
            print(f"scene {i}: waiting for video...")
            time.sleep(self.poll)
            op = self.client.operations.get(op)
        vid = op.response.generated_videos[0]
        self.client.files.download(file=vid.video)
        path = os.path.join(self.scenes_dir, f"scene{i}.mp4")
        vid.video.save(path)
        return path

    def evaluate_scene(self, s, img):
        from google.genai import types
        with open(img, "rb") as f:
            part = types.Part.from_bytes(data=f.read(), mime_type="image/png")
        r = self.client.models.generate_content(model=self.text_model, contents=[
            part, f"Score 1-10 how well this frame communicates: {s.get('subject','')} "
                  f"{s.get('action','')}. Reply with only the number."])
        m = re.search(r"\d+(\.\d+)?", r.text or "")
        return float(m.group()) if m else 0.0

    def stitch(self, clips, out):
        lst = os.path.join(self.scenes_dir, "list.txt")
        with open(lst, "w") as f:
            for c in clips:
                f.write(f"file '{os.path.abspath(c)}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", out], check=True)
        return out

    def slideshow(self, images, out, seconds=6):
        lst = os.path.join(self.scenes_dir, "slides.txt")
        with open(lst, "w") as f:
            for im in images:
                f.write(f"file '{os.path.abspath(im)}'\nduration {seconds}\n")
            f.write(f"file '{os.path.abspath(images[-1])}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-vf", "scale=1280:720,format=yuv420p", "-r", "25", out], check=True)
        return out

    # ---- orchestration -------------------------------------------------
    def scene_tasks(self, slideshow):
        def t_image(ctx):
            return {"img": self.scene_image(ctx["scene"], ctx["i"])}

        def t_eval(ctx):
            return {"score": self.evaluate_scene(ctx["scene"], ctx["img"])}

        def t_regen(ctx):
            return {"img": self.scene_image(ctx["scene"], ctx["i"])}

        def t_collect(ctx):
            ctx["images"].append(ctx["img"])

        def t_video(ctx):
            ctx["clips"].append(self.scene_video(ctx["scene"], ctx["i"], ctx["img"]))

        return [Task("scene_image", t_image, retries=1),
                Task("evaluate_frame", t_eval),
                Task("regenerate_if_weak", t_regen, when=lambda c: c.get("score", 10) < 6),
                Task("collect_frame", t_collect),
                Task("scene_video", t_video, retries=1, when=lambda c: not slideshow)]

    def run(self, slideshow=False):
        out = os.path.join(self.outdir, "how_it_works.mp4")
        self.orch = Orchestrator("video_agent", os.path.join(self.outdir, "video_agent_trace.json"))
        ctx = {"images": [], "clips": []}

        def t_plan(c):
            return {"scenes": self.plan_scenes()}

        def t_assemble(c):
            with open(os.path.join(self.outdir, "video_plan.json"), "w") as f:
                json.dump(c["scenes"], f, indent=2)
            res = (self.slideshow(c["images"], out) if slideshow
                   else self.stitch(c["clips"], out))
            return {"out": res}

        try:
            self.orch.run([Task("plan_scenes", t_plan, retries=1)], ctx)
            for i, s in enumerate(ctx["scenes"], 1):
                ctx.update({"i": i, "scene": s, "round": i, "score": 10})
                self.orch.run(self.scene_tasks(slideshow), ctx)
            self.orch.run([Task("assemble", t_assemble)], ctx)
        finally:
            self.orch.save()
        return ctx["out"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the 'how it works' video.")
    ap.add_argument("--scenes", type=int, default=4)
    ap.add_argument("--slideshow", action="store_true", help="skip Veo, build from images")
    ap.add_argument("--outdir", default="outputs")
    a = ap.parse_args()
    print("video ->", VideoAgent(outdir=a.outdir, n_scenes=a.scenes).run(slideshow=a.slideshow))
