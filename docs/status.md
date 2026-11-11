# Current status

> **Role: current state.** The one place for "where are we now". Update this file whenever something changes; other files link here instead of repeating numbers. New to the project: [handoff.md](handoff.md). History: [log.md](log.md); open work: [todo.md](todo.md). Last update: 2026-11-11 (first-draft hand-off).

**Goal (the loop):** one text prompt → a coherent layered scene → edit single layers (re-prompt, move, resize) → recomposite → story events change the scene. Free hardware: Kaggle 2× T4 (fp16 only) and a CPU laptop. No user study is planned; the prototype and its technical measurements are the contribution ([research/research-gap.md](research/research-gap.md)).

**Shared test scene:** fox & cottage (storybook style, **made by SDXL-Turbo**, seed 13), chosen 2026-11-09: [../prototype/test_scene/fox_cottage.png](../prototype/test_scene/fox_cottage.png), with names, hand-drawn boxes and caption in [fox_cottage.json](../prototype/test_scene/fox_cottage.json). Which model made which part of every picture in the model pages: [models/provenance.md](models/provenance.md).

**Recommended core path (proposal, the user decides):** SDXL-Turbo makes the first picture → Qwen-Image-2.1 splits and modifies it → Stable-Layers / CLD as optional splitters → IC-Light, shadow layers and `relocate()` on single layers; RevealLayer for inpainting. Reasoning and keep / explore / drop per model: [models/pipeline-plan.md](models/pipeline-plan.md).

## Each step of the loop

| Loop step | What works now | Speed (free hardware, warm model) | Details |
|---|---|---|---|
| Prompt → objects | the player names the objects (no language model; the old Ollama planner was dropped, [concepts/ollama-option.md](ideas-considered/ollama-option.md)) | instant | [concepts/pipeline.md](concepts/pipeline.md) |
| Prompt → whole image | **SDXL-Turbo** (fast first step); Qwen-Image-2.1 text to image | SDXL-Turbo 1.1-1.5 s on a T4 (its own Kaggle server, wired into the app); Qwen-2.1 17-23 s | [models/sdxl-turbo.md](models/sdxl-turbo.md) |
| Image → layers | **Qwen-Image-2.1 extraction** (clean on the daylight scene, weaker on night / rain edits); **Stable-Layers at 640 px** (one clean layer per object on the scene and on the edits); CLD and SAM2 + Qwen-2.1 as options | Qwen-2.1 118 s (four objects + background); Stable-Layers about 100 s (Euler) / 178 s (Heun); CLD 116-459 s; SAM2 3 s | [models/qwen-image-2.1.md](models/qwen-image-2.1.md), [models/stable-layers.md](models/stable-layers.md) |
| Hidden parts / background without the objects | Qwen-2.1 ("remove X", "extract only X without Y"); RevealLayer's filled backgrounds (inpainting role) | about 24 s per call; RevealLayer 85-358 s | [models/amodal-fill.md](models/amodal-fill.md), [models/revealayer.md](models/revealayer.md) |
| Re-prompt / edit one layer | **Qwen-Image-2.1 RGBA edit** with an alpha check-and-retry (10 of 10 edits accepted) | 22-29 s per edit | [models/qwen-image-2.1.md](models/qwen-image-2.1.md) |
| Move / resize a layer | direct manipulation (instant, in the app); `relocate()` (warp + SDXL re-harmonise, LayerDiffuse SDXL engine) is a server route, not in the app; a Qwen-2.1 harmonise gives a convincing shadow but redraws the picture | `relocate()` 3.4 s; Qwen-2.1 22-29 s | [models/relocate-harmonise.md](models/relocate-harmonise.md) |
| Relight / shadows | **Qwen-2.1 per-layer relight** (best on night and rain objects); **IC-Light** kept pending more tests; procedural shadow layer (multiply option) | 22-26 s per layer; IC-Light about 45 s per layer on the CPU; shadow 0.5 s for five layers | [models/relight-ic-light.md](models/relight-ic-light.md), [models/shadow-layers.md](models/shadow-layers.md) |
| Story events | Qwen-2.1 whole-scene edit (night, heavy rain keep the composition) then a split; per-layer relight; LLM router + instant CPU previews (router not wired into the app) | edit about 22 s + split about 100-180 s | [concepts/editing.md](concepts/editing.md) |
| Recomposite | alpha compositing in code | instant | — |
| Measure drift over many edits | harness + first real run (6 fox moves): persistent layers 60 dB outside the edit, re-decompose every turn 59 → 28 dB, flat Qwen-2.1 20 → 14 dB with the fox duplicated at turn 5; LPIPS / DINO agree | one scene, arms A, B and C | [research/drift-evaluation.md](research/drift-evaluation.md) |

## Each model: state and role

The full measured table is generated in [models/README.md](models/README.md); the method overview is [research/papers-survey.md](research/papers-survey.md). Verdict notes by the user are under the role line of each factsheet.

| Model | Role in the plan | Best measured result | Factsheet |
|---|---|---|---|
| SDXL-Turbo | first image (text, image to image) | 1.1-1.5 s per 512 px image on a T4; image to image replaces the scene | [→](models/sdxl-turbo.md) |
| Qwen-Image-2.1 | **core**: edit, extract, remove, relight, amodal, text to image | see the table above | [→](models/qwen-image-2.1.md) |
| Stable-Layers | optional splitter (clean on the scene and on story edits) | 640 px, 4 steps: sky / ground / cottage / tree / fox as layers, about 100 s | [→](models/stable-layers.md) |
| CLD | optional splitter | decent layers at 4-16 steps (116-459 s), invents a different background | [→](models/cld.md) |
| Qwen-Image-Layered (base) | in contention (inconsistent) | good on the forest scene; no object layers on the fox scene at 384-640 px | [→](models/qwen-image-layered.md) |
| RevealLayer | inpainting (filled backgrounds) | clean filled backgrounds, layers follow boxes; 85-358 s | [→](models/revealayer.md) |
| SAM2 + Grounding DINO (+ LaMa) | fast masks | 3 s by name; blurry fill, hidden parts missing | [→](models/sam2-lama.md), [→](models/sam2-lama.md) |
| IC-Light | relight, kept pending more tests | night grade + IC-Light gives a cool cast; poor on rain objects | [→](models/relight-ic-light.md) |
| `relocate()` (LayerDiffuse SDXL) | optional re-harmonise step | 3.4 s per move | [→](models/relocate-harmonise.md) |
| Shadow layers | helper | 0.5 s for five layers | [→](models/shadow-layers.md) |
| SDXL-inpaint | maybe usable (user) | fills of the cottage's hidden part | [→](models/amodal-fill.md) |
| Qwen Lightning | candidate to drop | no object layers at 384, 512 or 640 px; story composites not improved | [→](models/qwen-lightning.md) |
| LayerD | limited; look a little more | peels the fox with generic matting, rest one layer | [→](ideas-considered/models/layerd.md) |
| ART+, LayerDiffuse SDXL (generator and effect layers), LayerDiffuse-Flux | not pursued (user) | — | [→](ideas-considered/models/art-plus.md), [→](ideas-considered/models/layerdiffuse-sdxl.md), [→](ideas-considered/models/layerdiffuse-flux.md) |
| PSDiffusion, DreamLayer, OmniPSD, LASAGNA, LayerFusion … | no weights / code | — | [papers-survey §2](research/papers-survey.md#2-methods-we-cannot-run-no-weights-or-code) |

## Infrastructure and live measurements

- **Kaggle:** 2× T4, 30 GPU-h/week (idle time counts), **max 2 batch GPU sessions at once**; benchmark notebooks are generated by `prototype/tools/make_profile_notebook.py` and pushed with the CLI; the app builds and pushes its serve notebooks itself ([guides/kaggle.md](guides/kaggle.md), [../prototype/README.md](../prototype/README.md)). TPU: CLI batch runs got no TPU and the interactive session sat at queue position 1510 ([research/hosting.md](research/hosting.md#3-tpu)).
- **App:** a thin client; the models run in one Kaggle session (profile `studio`: SDXL-Turbo with CPU offload + Qwen-Image-2.1) that the app starts and stops with the user's Kaggle account; weights come from attached notebook outputs; idle stop after 20 minutes; Stop works in every state. The two-session setup (`sdxl-turbo`, `qwen21`) remains as a fallback.

Run live on 2026-11-11 (`prototype/tools/live_check.py` and through the real page):

| Session | Start to ready | Measured |
|---|---|---|
| SDXL-Turbo alone | 186 s (weights copied to local disk first; read straight from the input mount it took 416 s) | 2.8-3.4 s per picture through the tunnel, image to image 4.6 s ([img/live_check_sdxl_turbo.jpg](img/live_check_sdxl_turbo.jpg)) |
| Qwen-Image-2.1 alone | 19 min from the button, about 12 of them Kaggle's own start-up; 379 s of loading in the notebook (weights ready 75 s) | split of 2 objects + background 79 s, one layer edit 25 s ([img/live_check_qwen21.jpg](img/live_check_qwen21.jpg)) |
| **Both in one session (`studio`)** | 288 s after re-attaching; Kaggle queued the start about 25 minutes first | free GPU memory after loading 8.8 GiB on GPU 0 and 0.7 GiB on GPU 1; pictures 6-8 s (3 s in a dedicated session), image to image 8.4 s, split 69 s, edit 24 s; pictures made after the Qwen split and edit still worked, so SDXL-Turbo fits next to Qwen ([img/live_check_studio.jpg](img/live_check_studio.jpg)) |

The new page, driven live: text to image with 2 versions (about 7 s each); a sketch drawn on the canvas (a house and a pine tree) became 2 pictures that follow the drawing (image to image, strength 0.8); the split of the fox & cottage picture; a layer edit with 2 versions added 2 variants and the editor reloaded the newest; Stop from the page ended the session. Found and fixed by that run: hidden splitter inputs arrive as nothing (the split crashed on the empty boxes field), and faint stray pixels stretched a layer's handles (the box and pivot now ignore alpha below 24). Quality notes: the cottage layer carried a bare tree, the background kept the tree and a small house, and the "white fox" edit came back orange.

- **Repo:** github.com/CubePillow/ttrpg-layered-scenes (the shared repository); the untouched reference history is `github.com/MarkAndreDuesing/layer-prototype`.
