from types import SimpleNamespace


def text_resp(t):
    return SimpleNamespace(text=t, candidates=[])


def img_resp(data=b"\x89PNG"):
    part = SimpleNamespace(inline_data=SimpleNamespace(data=data))
    return SimpleNamespace(text=None, candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])


def empty_resp():
    return SimpleNamespace(text="", candidates=[])


class FakeVideo:
    def save(self, path):
        with open(path, "wb") as f:
            f.write(b"MP4")


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, model, contents):
        self.calls.append(model)
        return self.responses.pop(0)

    def generate_videos(self, model, prompt, image, config):
        self.calls.append(model)
        return SimpleNamespace(done=True, response=SimpleNamespace(
            generated_videos=[SimpleNamespace(video=FakeVideo())]))


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)
        self.files = SimpleNamespace(download=lambda file: None)
        self.operations = SimpleNamespace(get=lambda op: op)
