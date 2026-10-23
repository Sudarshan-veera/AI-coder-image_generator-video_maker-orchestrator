import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
for d in ("harness", "image_agent", "video_agent"):
    sys.path.insert(0, os.path.join(ROOT, d))
