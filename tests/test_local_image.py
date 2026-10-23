import os
from PIL import Image
from common import local_image as LI


def test_construction_needs_no_gpu_or_torch():
    g = LI.LocalImageGen()
    assert g.model_id and g.steps >= 1


def test_make_logo_adds_name_on_1024_canvas(tmp_path):
    em = tmp_path / "e.png"
    Image.new("RGB", (512, 512), (10, 120, 200)).save(em)
    out = LI.make_logo(str(em), "A Very Long Team Name That Must Shrink To Fit", str(tmp_path / "l.png"))
    assert Image.open(out).size == (1024, 1024)


def test_compose_scene_is_1280x720(tmp_path):
    bg = tmp_path / "bg.png"
    Image.new("RGB", (768, 432), (30, 30, 80)).save(bg)
    ov = LI.compose_overlay("Title", ["plan", "research", "extract", "filter", "rank", "enrich", "critic", "report"],
                            "A caption " * 12, str(tmp_path / "o.png"), note="note")
    out = LI.compose_scene(str(bg), ov, str(tmp_path / "f.png"))
    assert Image.open(out).size == (1280, 720)
