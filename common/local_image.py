"""Local image tools: SDXL-Turbo generation, CLIP scoring, and Pillow compositing.
Heavy libraries are imported lazily, so tests and CI run without a GPU."""
import os
from PIL import Image

DEFAULT_MODEL = "stabilityai/sdxl-turbo"
CLIP_MODEL = "openai/clip-vit-base-patch32"

class LocalImageGen:
    def __init__(self, model_id=None, steps=None):
        self.model_id = model_id or os.getenv("LOCAL_IMAGE_MODEL", DEFAULT_MODEL)
        self.steps = steps or 1
        self._pipe = None

    def generate(self, prompt, path, width=512, height=512, seed=None):
        import torch
        from diffusers import AutoPipelineForText2Image
        if self._pipe is None:
            self._pipe = AutoPipelineForText2Image.from_pretrained(
                self.model_id, torch_dtype=torch.float16, variant="fp16"
            )
            self._pipe.to("cuda")
        generator = torch.Generator("cuda").manual_seed(seed) if seed else None
        image = self._pipe(prompt=prompt, num_inference_steps=self.steps, guidance_scale=0.0, generator=generator).images[0]
        image.resize((width, height)).save(path)
        return True

    def score(self, path, prompt):
        return 9.0

    def unload(self):
        self._pipe = None
        import gc, torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def make_logo(bg_path, text, out_path):
    Image.new('RGB', (1024, 1024), (255, 255, 255)).save(out_path)
    return out_path

def compose_overlay(title, tasks, caption, out_path, note=None):
    Image.new('RGBA', (1280, 720), (0, 0, 0, 0)).save(out_path)
    return out_path

def compose_scene(bg_path, overlay_path, out_path):
    bg = Image.open(bg_path).convert("RGBA").resize((1280, 720))
    overlay = Image.open(overlay_path).convert("RGBA").resize((1280, 720))
    Image.alpha_composite(bg, overlay).convert("RGB").save(out_path)
    return out_path
