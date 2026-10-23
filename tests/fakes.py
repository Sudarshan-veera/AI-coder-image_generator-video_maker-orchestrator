import wave
from PIL import Image


class FakeImageGen:
    def __init__(self, scores=None):
        self.scores = list(scores or [])
        self.calls = []

    def generate(self, prompt, path, width=512, height=512, seed=None):
        self.calls.append((prompt, seed))
        Image.new("RGB", (width, height), (40, 90, 160)).save(path)
        return True

    def score(self, path, prompt):
        return self.scores.pop(0) if self.scores else 9.0

    def unload(self):
        pass


class FakeTTS:
    def speak(self, text, path):
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x00\x00" * 8000)          # 1 second of silence
        return 1.0


class FakeAnimator:
    def __init__(self, fail=False):
        self.calls, self.fail = 0, fail

    def animate(self, image, prompt, out, seconds=3):
        self.calls += 1
        if self.fail:
            raise RuntimeError("out of memory")
        open(out, "wb").write(b"MP4")


def fake_llm(reply="ok"):
    return lambda prompt, **kw: reply
