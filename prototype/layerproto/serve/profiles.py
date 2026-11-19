"""Registry of server profiles (one profile per Kaggle session) and their fox & cottage benchmark cases (paths A and B).

A profile = pip packages + Kaggle kernel sources (pre-downloaded weights) + a factory that returns a decomposer + the benchmark
cases. `tools/make_profile_notebook.py --profile NAME --mode bench|serve` turns one into a notebook.

Paths (see docs/models/TEMPLATE.md): A = best case, up to 8 minutes of compute per image; B = live-demo budget, about 30 s of
compute per image. Compute = the generation call only, never the model load.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..backends.decomposer import DecomposeParams

CAPTION = ("Storybook illustration of a thatched stone cottage with a large leafy tree on the right, a stone gate arch on the left, "
           "small village houses behind, a cobblestone path leading into the foreground and a red fox standing on the path.")
NAMES = ["village houses", "cottage", "stone gate arch", "big tree", "red fox"]
BOXES = [[0, 195, 115, 280], [95, 100, 475, 330], [62, 245, 150, 322], [180, 0, 512, 352], [205, 325, 375, 452]]


@dataclass
class Case:
    tag: str                       # file name stem, e.g. "A"
    path: str                      # "A" best case or "B" live-demo budget
    params: DecomposeParams
    note: str = ""
    repeats: int = 2               # the first call warms up (kernels, caches); report the last
    scene: str = "fox_cottage"     # image name under prototype/test_scene (the notebook zip carries Profile.files)


@dataclass
class Profile:
    name: str
    pip: list = field(default_factory=list)      # pip groups: each string is one `pip install` call (args split on spaces, as one resolution)
    env: dict = field(default_factory=dict)       # environment variables set before anything imports torch
    kernel_sources: list = field(default_factory=list)
    gpu: str = "NvidiaTeslaT4"
    factory: str = ""              # "module:function" returning a decomposer callable (image, DecomposeParams) -> layers
    cases: list = field(default_factory=list)
    files: dict = field(default_factory=dict)       # extra files for the zip: {path inside prototype/: path relative to the repo root}
    doc: str = ""
    weights: list = field(default_factory=list)   # weight notebooks (slugs, owner added at build time) attached as input: no re-download
    kind: str = "decompose"        # "decompose" (role split: /decompose, /edit), "generate" (role generate: /txt2img, /img2img) or "both" (studio)


def P(**kw):
    return DecomposeParams(caption=CAPTION, **kw)


PROFILES = {
    "qwen-layered": Profile(
        name="qwen-layered",
        pip=["diffusers==0.37.0 transformers>=4.51 accelerate gguf"],
        kernel_sources=["markandreduesing/qwen-layered-weights-transformer", "markandreduesing/qwen-layered-weights-base"],
        factory="layerproto.serve.qwen_layered:make",
        doc="docs/models/qwen-image-layered.md (also stable-layers.md, qwen-lightning.md)",
        cases=[
            Case("qwenlayered_A", "A", P(method="qwen-layered", resolution=512, n_layers=5, steps=16), "512 px, 5 layers, 16 Euler steps"),
            Case("qwenlayered_B", "B", P(method="qwen-layered", resolution=384, n_layers=4, steps=4), "384 px, 4 layers, 4 Euler steps"),
            Case("stablelayers_A", "A", P(method="stable-layers", resolution=512, n_layers=5, steps=8, sampler="heun"), "512 px, 5 layers, 8 Heun steps"),
            Case("stablelayers_B", "B", P(method="stable-layers", resolution=384, n_layers=5, steps=3), "384 px, 5 layers, 3 Euler steps"),
            Case("lightning_A", "A", P(method="qwen-lightning", resolution=512, n_layers=5, steps=4), "512 px, 5 layers, 4 steps"),
            Case("lightning_B", "B", P(method="qwen-lightning", resolution=384, n_layers=5, steps=2), "384 px, 5 layers, 2 steps"),
        ]),
    "studio": Profile(
        name="studio",
        pip=["transformers>=5.17 gguf>=0.10 accelerate git+https://github.com/huggingface/diffusers"],
        weights=["weights-qwen21-text-encoder", "weights-qwen21-parts", "weights-sdxl-turbo"],
        factory="layerproto.serve.studio:make",
        kind="both",
        doc="docs/models/sdxl-turbo.md, docs/models/qwen-image-2.1.md (one session: SDXL-Turbo with CPU offload next to Qwen-Image-2.1)",
        cases=[]),
    "sdxl-turbo": Profile(
        name="sdxl-turbo",
        pip=["diffusers==0.37.0 transformers>=4.51 accelerate"],
        weights=["weights-sdxl-turbo"],
        factory="layerproto.serve.sdxl_turbo:make",
        kind="generate",
        doc="docs/models/sdxl-turbo.md",
        cases=[]),
    "qwen21": Profile(
        name="qwen21",
        pip=["transformers>=5.17 gguf>=0.10 accelerate git+https://github.com/huggingface/diffusers"],
        weights=["weights-qwen21-text-encoder", "weights-qwen21-parts"],
        factory="layerproto.serve.qwen21:make",
        doc="docs/models/qwen-image-2.1.md",
        cases=[
            Case("qwen21_A", "A", P(method="qwen21-extract", names=NAMES[1:], boxes=BOXES[1:]), "background + 4 objects, 8 steps, 512 px"),
            Case("qwen21_B", "B", P(method="qwen21-extract", names=["red fox"], boxes=[BOXES[4]]), "one object per request, 8 steps, 512 px", repeats=2),
        ]),
    "sam2": Profile(
        name="sam2",
        pip=["git+https://github.com/facebookresearch/sam2.git", "--no-deps simple-lama-inpainting", "fire", "diffusers==0.37.0", "fastapi uvicorn"],
        factory="layerproto.serve.sam2:make",
        doc="docs/models/sam2-lama.md (also grounding-dino.md, amodal-fill.md)",
        cases=[
            Case("sam2_A", "A", P(method="sam2-lama", names=NAMES, boxes=BOXES), "hand boxes -> SAM2 + LaMa"),
            Case("sam2_B", "B", P(method="sam2-lama", names=NAMES), "names -> Grounding DINO -> SAM2 + LaMa"),
            Case("sam2_amodal", "A", P(method="sam2-lama", names=NAMES[1:], boxes=BOXES[1:], amodal=True), "hand boxes + SDXL-inpaint amodal fill", repeats=1),
        ]),
    "cld": Profile(
        name="cld",
        pip=["transformers==4.57.1 diffusers==0.32.2 peft==0.14.0 gguf>=0.10 sentencepiece protobuf mmengine gdown einops"],
        env={"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"},
        factory="layerproto.serve.cld:make",
        doc="docs/models/cld.md",
        cases=[
            Case("cld_A", "A", P(method="cld", boxes=[BOXES[0], [0, 330, 300, 512], BOXES[1], [0, 255, 512, 330], BOXES[2], BOXES[3], BOXES[4]],
                                 resolution=512, steps=16), "512 px, 7 boxes, 16 steps (prompt embeddings cached on the second run)", repeats=2),
            Case("cld_B", "B", P(method="cld", boxes=BOXES, resolution=512, steps=4), "512 px, 5 boxes, 4 steps (cheapest setting, quality not checked)", repeats=2),
        ]),
    "artplus": Profile(
        name="artplus",
        pip=["transformers==4.57.1 diffusers==0.32.2 peft==0.14.0 gguf>=0.10 sentencepiece protobuf mmengine gdown einops"],
        env={"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"},
        factory="layerproto.serve.artplus:make",
        doc="docs/ideas-considered/models/art-plus.md",
        cases=[
            Case("artplus_A", "A", P(method="artplus", boxes=BOXES, resolution=512, steps=16), "512 px, 5 boxes, 16 steps", repeats=1),
            Case("artplus_B", "B", P(method="artplus", boxes=BOXES, resolution=512, steps=4), "512 px, 5 boxes, 4 steps (cheapest setting, quality not checked)", repeats=2),
        ]),
    "reveallayer": Profile(
        name="reveallayer",
        pip=["transformers==4.57.1 gguf>=0.10 peft==0.15.2 mmengine==0.10.7 einops sentencepiece protobuf"],
        env={"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"},
        factory="layerproto.serve.reveallayer:make",
        doc="docs/models/revealayer.md",
        cases=[
            Case("reveallayer_A", "A", P(method="reveallayer", boxes=BOXES, steps=16, guidance=3.5, resolution=512), "512 px, 5 boxes, true_gs 3.5, 16 steps", repeats=1),
            Case("reveallayer_B", "B", P(method="reveallayer", boxes=BOXES, steps=6, guidance=1.0, resolution=512), "512 px, 5 boxes, true_gs 1.0, 6 steps (cheapest setting, quality not checked)", repeats=2),
        ]),
    "qwen-layered-diag": Profile(
        name="qwen-layered-diag",
        pip=["diffusers==0.37.0 transformers>=4.51 accelerate gguf"],
        kernel_sources=["markandreduesing/qwen-layered-weights-transformer", "markandreduesing/qwen-layered-weights-base"],
        factory="layerproto.serve.qwen_layered:make_diag",
        files={"test_scene/forest.png": "prototype/test_scene/forest.png"},
        doc="docs/models/qwen-image-layered.md (diagnosis of the weak fox & cottage split)",
        cases=[
            Case("diag_forest_384", "A", DecomposeParams(caption='An impressionist oil painting of a forest clearing at night: tall pine trees and bare trees, a full moon and stars in a blue sky, distant mountains, a campfire with logs in the middle, a wooden chair next to it, rocks and fallen branches on the ground.', method="qwen-layered", resolution=384, n_layers=4, steps=4), "control: forest, 384 px, 4 layers, 4 steps (the old good setting)", repeats=1, scene="forest"),
            Case("diag_fox_384", "A", P(method="qwen-layered", resolution=384, n_layers=4, steps=4), "fox, 384 px, 4 layers, 4 steps", repeats=1),
            Case("diag_fox_384_nocaption", "A", DecomposeParams(caption="", method="qwen-layered", resolution=384, n_layers=4, steps=4), "fox, 384 px, empty caption", repeats=1),
            Case("diag_fox_640_4st", "A", P(method="qwen-layered", resolution=640, n_layers=4, steps=4), "fox, 640 px (native), 4 layers, 4 steps", repeats=1),
            Case("diag_fox_640_20st", "A", P(method="qwen-layered", resolution=640, n_layers=4, steps=20), "fox, 640 px, 4 layers, 20 steps", repeats=1),
            Case("diag_fox_640_cfg4", "A", P(method="qwen-layered", resolution=640, n_layers=4, steps=12, cfg=4.0), "fox, 640 px, 12 steps, CFG 4", repeats=1),
        ]),
    "qwen-layered-640": Profile(
        name="qwen-layered-640",
        pip=["diffusers==0.37.0 transformers>=4.51 accelerate gguf"],
        kernel_sources=["markandreduesing/qwen-layered-weights-transformer", "markandreduesing/qwen-layered-weights-base"],
        factory="layerproto.serve.qwen_layered:make_640",
        files={"test_scene/night.png": "prototype/test_scene/night.png",
               "test_scene/rain.png": "prototype/test_scene/rain.png"},
        doc="docs/models/stable-layers.md, qwen-lightning.md (native 640 px, fox scene and story composites)",
        cases=[
            Case("w640_fox_base", "A", DecomposeParams(caption=CAPTION, method="qwen-layered", resolution=640, n_layers=5, steps=4, sampler="euler"), "fox, base, 4 Euler steps", repeats=1, scene="fox_cottage"),
            Case("w640_fox_stable_euler", "A", DecomposeParams(caption=CAPTION, method="stable-layers", resolution=640, n_layers=5, steps=4, sampler="euler"), "fox, Stable-Layers, 4 Euler steps", repeats=1, scene="fox_cottage"),
            Case("w640_fox_stable_heun", "A", DecomposeParams(caption=CAPTION, method="stable-layers", resolution=640, n_layers=5, steps=4, sampler="heun"), "fox, Stable-Layers, 4 Heun steps", repeats=1, scene="fox_cottage"),
            Case("w640_fox_light4", "A", DecomposeParams(caption=CAPTION, method="qwen-lightning", resolution=640, n_layers=5, steps=4, sampler="euler"), "fox, Lightning, 4 steps", repeats=1, scene="fox_cottage"),
            Case("w640_fox_light2", "A", DecomposeParams(caption=CAPTION, method="qwen-lightning", resolution=640, n_layers=5, steps=2, sampler="euler"), "fox, Lightning, 2 steps", repeats=1, scene="fox_cottage"),
            Case("w640_night_base", "A", DecomposeParams(caption=CAPTION + " Now at night, moonlit, lantern light.", method="qwen-layered", resolution=640, n_layers=5, steps=4, sampler="euler"), "night composite, base, 4 Euler steps", repeats=1, scene="night"),
            Case("w640_night_stable_heun", "A", DecomposeParams(caption=CAPTION + " Now at night, moonlit, lantern light.", method="stable-layers", resolution=640, n_layers=5, steps=4, sampler="heun"), "night composite, Stable-Layers, 4 Heun steps", repeats=1, scene="night"),
            Case("w640_night_light4", "A", DecomposeParams(caption=CAPTION + " Now at night, moonlit, lantern light.", method="qwen-lightning", resolution=640, n_layers=5, steps=4, sampler="euler"), "night composite, Lightning, 4 steps", repeats=1, scene="night"),
            Case("w640_rain_base", "A", DecomposeParams(caption=CAPTION + " Now in heavy rain, grey sky.", method="qwen-layered", resolution=640, n_layers=5, steps=4, sampler="euler"), "rain composite, base, 4 Euler steps", repeats=1, scene="rain"),
            Case("w640_rain_stable_heun", "A", DecomposeParams(caption=CAPTION + " Now in heavy rain, grey sky.", method="stable-layers", resolution=640, n_layers=5, steps=4, sampler="heun"), "rain composite, Stable-Layers, 4 Heun steps", repeats=1, scene="rain"),
            Case("w640_rain_light4", "A", DecomposeParams(caption=CAPTION + " Now in heavy rain, grey sky.", method="qwen-lightning", resolution=640, n_layers=5, steps=4, sampler="euler"), "rain composite, Lightning, 4 steps", repeats=1, scene="rain"),
        ]),
    "qwen21-story": Profile(
        name="qwen21-story",
        pip=["transformers>=5.17 gguf>=0.10 accelerate git+https://github.com/huggingface/diffusers"],
        factory="layerproto.serve.qwen21:make",
        files={"test_scene/night.png": "prototype/test_scene/night.png",
               "test_scene/rain.png": "prototype/test_scene/rain.png"},
        doc="docs/models/qwen-image-2.1.md (split of the night and rain edits, for the comparison with Stable-Layers / CLD)",
        cases=[
            Case("q21story_night", "A", P(method="qwen21-extract", names=NAMES[1:], boxes=BOXES[1:]), "night edit: background + 4 objects, 8 steps, 512 px", repeats=1, scene="night"),
            Case("q21story_rain", "A", P(method="qwen21-extract", names=NAMES[1:], boxes=BOXES[1:]), "rain edit: background + 4 objects, 8 steps, 512 px", repeats=1, scene="rain"),
        ]),
}
