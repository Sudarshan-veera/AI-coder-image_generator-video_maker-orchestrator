"""Optional: image-to-video motion with LTX-Video through diffusers (needs ~10 GB VRAM, slow)."""
import gc, os


class LTXAnimator:
    MODEL = os.getenv("LOCAL_VIDEO_MODEL", "Lightricks/LTX-Video")

    def __init__(self):
        self._pipe = None

    def animate(self, image_path, prompt, out_path, seconds=3):
        import torch
        from diffusers import LTXImageToVideoPipeline
        from diffusers.utils import export_to_video, load_image
        if self._pipe is None:
            self._pipe = LTXImageToVideoPipeline.from_pretrained(self.MODEL, torch_dtype=torch.bfloat16)
            self._pipe.enable_model_cpu_offload()
            self._pipe.vae.enable_tiling()
        image = load_image(image_path).resize((704, 480))
        frames = self._pipe(image=image, prompt=prompt,
                            negative_prompt="worst quality, blurry, jittery, distorted",
                            width=704, height=480, num_frames=24 * seconds + 1,
                            num_inference_steps=30).frames[0]
        export_to_video(frames, out_path, fps=24)
        return out_path

    def unload(self):
        self._pipe = None
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:                                   # noqa: BLE001
            pass
