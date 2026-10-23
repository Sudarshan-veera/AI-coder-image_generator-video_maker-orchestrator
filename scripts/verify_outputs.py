"""Checks the real outputs of the three agents. Run after the agents have run."""
import glob, json, os, subprocess, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "outputs"
fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def tasks(path):
    try:
        return {e["task"] for e in json.load(open(path)) if e["status"] == "ok"}
    except Exception:
        return set()


# --- coding agent -------------------------------------------------------
files = glob.glob(os.path.join(OUT, "*_top10.json"))
check("startup list file exists", bool(files))
if files:
    rows = json.load(open(files[0]))
    check("10 startups listed", len(rows) == 10, f"got {len(rows)}")
    check("no public companies", not any(str(r.get("status")).lower() == "public" for r in rows))
    check("funding never equals valuation",
          not any(r.get("total_funding") not in (None, "unknown") and r.get("total_funding") == r.get("valuation") for r in rows))
    check("every row has sources", all(r.get("sources") for r in rows))
    check("every row has latest news", all(str(r.get("latest_news", "unknown")).lower() != "unknown" for r in rows))
check("coding agent tasks traced",
      {"plan", "research", "extract", "filter", "rank", "enrich", "critic", "report"} <= tasks(os.path.join(OUT, "trace.json")))

# --- image agent --------------------------------------------------------
logo = os.path.join(OUT, "team_logo.png")
check("logo exists", os.path.exists(logo))
if os.path.exists(logo):
    try:
        from PIL import Image
        w, h = Image.open(logo).size
        check("logo is a valid image >= 256px", min(w, h) >= 256, f"{w}x{h}")
    except Exception as e:
        check("logo is a valid image", False, str(e))
check("image agent tasks traced",
      {"brand_analysis", "design_concepts", "generate", "evaluate", "finalize"} <= tasks(os.path.join(OUT, "image_agent_trace.json")))

# --- video agent --------------------------------------------------------
video = os.path.join(OUT, "how_it_works.mp4")
check("video exists", os.path.exists(video))
if os.path.exists(video):
    try:
        d = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video]).decode().strip())
        check("video duration >= 5 s", d >= 5, f"{d:.1f}s")
    except Exception as e:
        check("video is readable by ffprobe", False, str(e))
check("video agent tasks traced",
      {"plan_scenes", "art", "compose_frame", "narrate", "render_clip", "assemble"} <= tasks(os.path.join(OUT, "video_agent_trace.json")))

print(f"\n{len(fails)} failed")
sys.exit(1 if fails else 0)
