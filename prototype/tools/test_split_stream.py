"""split_stream makes one layer per call (qwen21-extract `only`), the scene grows layer by layer, and editor autosaves in between are kept.
Run: python prototype/tools/test_split_stream.py   (no GPU)"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import Image  # noqa: E402

from layerproto.backends.decomposer import DecomposeParams  # noqa: E402
from layerproto.backends.qwen21_decomposer import Qwen21Decomposer  # noqa: E402
from layerproto.config import load_settings  # noqa: E402
from layerproto.engine import Engine  # noqa: E402
from layerproto.scene import Scene  # noqa: E402


class FakePipe:
    _execution_device = "cpu"

    def __init__(self):
        self.calls = []

    def __call__(self, prompt, image, **kw):
        self.calls.append(prompt)
        im = Image.new("RGBA", (512, 512), (200, 50, 50, 255))
        if "Remove" not in prompt:                         # an object: opaque in the left quarter only
            im.putalpha(Image.new("L", (512, 512), 0).point(lambda a: a))
            im.paste(Image.new("L", (128, 512), 255), (0, 0))
        return type("R", (), {"images": [im]})()


def main():
    S = load_settings()
    S.scenes_dir = tempfile.mkdtemp()
    eng = Engine(S)
    pipe = FakePipe()
    dec = Qwen21Decomposer(pipe)
    import torch  # noqa: F401  (the decomposer's _run uses it)
    eng.decomposer_for = lambda role="split": type("D", (), {"decompose": lambda self, im, p: dec(im, p)})()
    names = ["umbrella", "lounger"]
    sc = Scene(id="t1", user_input="x", refined_prompt="x", n_layers=3)
    sc.save(S.scenes_dir)
    sizes = []
    for sc in eng.split_stream(sc, Image.new("RGB", (512, 512)), DecomposeParams(method="qwen21-extract", names=names), versions=2):
        sizes.append(len(sc.layers))
        if len(sc.layers) == 2:                           # the editor autosaves while the split runs: the later layers must survive
            state = {"selected": None, "layers": [dict(id=l.id, name=l.name, visible=True, dx=0.1, dy=0, scale=1, rot=0) for l in sc.layers]}
            eng.apply_editor_state(Scene.load(f"{S.scenes_dir}/t1/scene.json"), state, keep_unknown=True)
    assert sizes[:3] == [1, 2, 3], sizes
    final = Scene.load(f"{S.scenes_dir}/t1/scene.json")
    assert [l.name for l in final.layers] == ["background", "umbrella", "lounger"], [l.name for l in final.layers]
    assert all(len(l.variants) == 2 for l in final.layers), [len(l.variants) for l in final.layers]
    assert final.layers[1].dx == 0.1
    assert len(pipe.calls) == 6, pipe.calls
    print("split stream test passed", sizes)


main()
