# Example runs in the page: fox & cottage and skeleton & campfire

> **Role: guide (medium).** Two end-to-end runs of the Gradio prototype (`python prototype/app.py`, then http://127.0.0.1:7870) with every input filled in, so anyone on the team can reproduce the test scenes. Setup first: [../../prototype/README.md](../../prototype/README.md). The two runs differ only in step 1: fox & cottage starts from **text**, skeleton & campfire from **prompt + sketch (image to image)**. The values come from `prototype/app.py`, `prototype/test_scene/fox_cottage.json` and `experiments/` (they arrive with the later pull requests of the stack); this page has not been run end to end in the shared repository.

## 0. Start the session (both runs)
1. In **Kaggle session**, press **Start (SDXL-Turbo + Qwen-Image-2.1)**.
2. Wait for ✅ *ready*: about 5 minutes of loading plus Kaggle's queue (up to 20 more minutes when Kaggle is busy).

## A. Fox & cottage (text to image)

### A1. The picture
SDXL-Turbo cannot reproduce the exact scene on the GPU (the original came from a CPU run), so there are two options.

**Option 1: generate it**

| Field | Value |
|---|---|
| Describe the scene | `Storybook illustration of a thatched stone cottage with a large leafy tree on the right, a stone gate arch on the left, small village houses behind, a cobblestone path leading into the foreground and a red fox standing on the path.` |
| Versions (different seeds) | `2` (up to `4` to get a good layout) |
| First seed | `13` |
| SDXL-Turbo steps | `4` |

Press **Make the picture from the text**, then click the version you like in the gallery. Draft pictures often contain a second fox; use more versions if so.

**Option 2: use the exact test picture** (recommended when comparing with the docs): upload `prototype/test_scene/fox_cottage.png` into the **Picture to split** box on the right.

### A2. Split
| Field | Value |
|---|---|
| Splitter | `Qwen-Image-2.1 (extract the objects you name)` (the default) |
| Objects to extract, comma separated, back to front | `village houses, cottage, stone gate arch, big tree, red fox` |
| Versions per layer | `1` |
| Resolution (px) | `512` |
| Steps | `4` |

Press **Split the picture into layers**: about 24 s per object plus one call for the background, so 2-3 minutes for five objects. The arch comes back too large (known issue, [../todo.md](../todo.md)). A shorter set from the live checks: `cottage, big tree, red fox`.

### A3. Work on the layers
1. In the editor, use **Move**, the corner handles and the round rotate handle, for example on the fox.
2. Pick the fox in the editor, then under **Edit the picked layer**:

| Field | Value |
|---|---|
| Change the picked layer | `make the fox white` or `the fox lit by a lantern from the left` |
| Versions | `2` |
| Seed | `42` |

Press **Edit the picked layer** (about 25 s per version) and click the variant you like in the **Variants** row.
3. **Export PNG**.

### Other splitters for this scene (optional)
Each starts its own Kaggle session: press **Start this splitter's Kaggle session** and wait for ✅ first.

| Splitter | Extra inputs |
|---|---|
| Stable-Layers | Layers `5`, Resolution `640`, Steps `4`, Sampler `euler`; the best split of this scene (about 100 s) |
| SAM2 + Grounding DINO + LaMa | the same names, or boxes `[[0,195,115,280],[95,100,475,330],[62,245,150,322],[180,0,512,352],[205,325,375,452]]` |
| RevealLayer or CLD | the same names and the boxes above (they need boxes) |

## B. Skeleton & campfire (prompt + sketch, image to image)

### B1. The picture
**Sketch:** `experiments/inputs/sketch_filled.png`, the coloured-background version. A raw, unfilled sketch gives a pale daytime scene; a filled one gives night with a moon ([../../experiments/README.md](../../experiments/README.md)). Drop it into the **Sketch** box; you can draw over it or use it as it is.

| Field | Value |
|---|---|
| Describe the scene | `one skeleton dancing next to a large campfire with a stone ring, campfire in the center, skeleton on the right side, night forest of tall pine trees, full moon and stars` |
| Sketch strength | `0.8` |
| SDXL-Turbo steps | `4` |
| Versions (different seeds) | `3` |
| First seed | `2024` |

Press **Make the picture from the sketch (image to image)**, then click the version you like.

- **Style prefix (optional):** put one in front of the prompt, for example `pixel art, retro 16-bit game scene,` or `impressionist oil painting, visible brushstrokes, soft light,`. With a filled sketch the differences are modest; hyperrealistic was never kept.
- **Seeds:** one skeleton and a central campfire held in 12 of 12 runs, but seed 2024 duplicated the skeleton in the old tests, so check every version and try `42` and `99` too (seed 42 gave 14 of the 27 kept images).
- **Strength:** at `0.8` the sketch guides the layout; raise it towards `0.95` to let the prompt override the sketch.
- **Text only:** leave the sketch empty and press **Make the picture from the text**; the layout is then poorly followed (skeleton and moon positions vary).

### B2. Split
| Field | Value |
|---|---|
| Splitter | `Qwen-Image-2.1 (extract the objects you name)` |
| Objects to extract, comma separated, back to front | `pine trees, campfire, skeleton` |
| Versions per layer | `1` |
| Resolution (px) | `512` |
| Steps | `4` |

Press **Split the picture into layers** (about 24 s per object plus the background). These object names have not been verified: the written-up Qwen-2.1 results are all on fox & cottage. If an object comes out empty or merged, try shorter names (`trees`, `fire`, `skeleton`).

**Splitter that suits this scene:** the notes say Qwen-Image-Layered does well on the forest and campfire pictures. Press **Start this splitter's Kaggle session**, then choose `Stable-Layers (Qwen-Image-Layered + LoRA)` or `Qwen-Image-Layered (all layers in one pass)` with Layers `4`, Resolution `384`, Steps `4`, Sampler `euler`.

### B3. Work on the layers
1. Move, resize or rotate the skeleton, for example to the left of the campfire.
2. **Change the picked layer:** `the skeleton wearing a red hat` or `the campfire burning with blue flames`; Versions `2`, Seed `42`; press **Edit the picked layer**. A blue-flame campfire edit worked in the earlier Qwen-2.1 tests.
3. **Export PNG**.

## Finish (both runs)
Press **Stop** in the Kaggle session panel. Idle time counts against the weekly Kaggle quota, and the session also stops itself after 20 idle minutes.
