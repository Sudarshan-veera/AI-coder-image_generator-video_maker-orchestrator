"""Generate any image from a prompt with the local diffusion model."""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.local_image import LocalImageGen

ap = argparse.ArgumentParser(description="Generate an image from a prompt (local SDXL-Turbo).")
ap.add_argument("prompt")
ap.add_argument("--out", default="outputs/custom_image.png")
ap.add_argument("--width", type=int, default=768)
ap.add_argument("--height", type=int, default=512)
ap.add_argument("--seed", type=int, default=1)
a = ap.parse_args()
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
gen = LocalImageGen()
gen.generate(a.prompt, a.out, a.width, a.height, a.seed)
gen.unload()
print(a.out)
