# Which model goes where: verdicts and the core path

> **Role: the verdict per model (2026-11-11, revised after the attribution audit [provenance.md](provenance.md)).** Built from the owner's assessments in the factsheets ([README](README.md)) and their measurements. The verdicts are the owner's decisions; the measurements are in the factsheets; the architecture is [../concepts/pipeline.md](../concepts/pipeline.md). Numbers are on the fox & cottage scene.

## 1. The core path

**SDXL-Turbo makes the first picture** (text, or a sketch or picture as image to image; 1.1-1.5 s per 512 px image on a T4 against 17-23 s for Qwen-2.1 text to image) **and Qwen-Image-2.1 splits and modifies it** ([sdxl-turbo.md](sdxl-turbo.md), [qwen-image-2.1.md](qwen-image-2.1.md)). SDXL-Turbo is not a layer model; its image to image regenerates the scene (the fox became a horse), so story edits stay with Qwen-2.1. Stable-Layers and CLD stay **options for splitting**. Measured: on the daylight scene Qwen-2.1 extraction gives a clean background and whole objects (118 s for four objects, arch mis-scaled); on the night and rain edits it left the cottage and tree in the background and invented a misplaced arch (139-184 s), while Stable-Layers at 640 px split both cleanly (about 100-180 s) ([stable-layers.md](stable-layers.md)). RevealLayer is kept for **inpainting** (filled backgrounds, hidden parts), not for splitting. LayerDiffuse SDXL stays only as the engine of `relocate()`.

**Timing consequence:** splitting a scene takes about 100 s, so it is done once per scene; the live loop works on the existing layers. Move and resize are instant (canvas editor), a relight preview is a CPU grade, and the slow steps are one Qwen-2.1 call (about 24 s) per layer or background. A story event that changes the whole scene costs one edit (22 s) plus a re-split, so it runs in the background while a preview is shown ([../concepts/editing.md](../concepts/editing.md)).

## 2. Verdict per model

| Model / approach | Verdict | Reason |
|---|---|---|
| Qwen-Image-2.1 | **Core**; keep developing | scene edit, story composites, image to image, add / remove / modify, background inpainting, amodal, relight; about 24 s per call, non-commercial licence |
| SDXL-Turbo | **Core**: first picture | fast; no layout control (often a second fox) |
| Stable-Layers (LoRA on the Qwen-Image-Layered weights) | **Optional splitter** | the only splitter that gave clean object layers at 640 px on the scene and on Qwen-2.1's night and rain edits; colour shift; about 100 s; needs the Qwen-Image-Layered weights |
| Qwen-Image-Layered (base) | **Keep in contention** | inconsistent: good on the forest, no object layers on the fox scene at any setting tried; to test: more scenes, a full-precision run |
| CLD | **Optional splitter** (unless Qwen-2.1 has an absolute advantage; runtime counts) | decent layers at 4-16 steps, an invented replacement background, 116-459 s, FLUX.1-dev non-commercial |
| RevealLayer | **Inpainting only** | clean filled backgrounds (the strongest background removal seen), layers follow boxes; 85-358 s, FLUX non-commercial |
| Grounding DINO + SAM2 | **Keep** (fast masks) | 3 s by name; fill and hidden parts are the weak part, so combine with a Qwen-2.1 fill |
| Shadow layers | **Core** (CPU helper) | instant, any layer |
| IC-Light + chroma fix | **Keep, tune further** | relights a daylight fox plausibly; on night and rain objects the Qwen-2.1 per-layer relight is better and IC-Light's rain objects stay pale ([relight-ic-light.md](relight-ic-light.md)) |
| `relocate()` / harmonise | **Optional step**; move / resize itself is direct manipulation | 3.4 s; runs on LayerDiffuse SDXL; a Qwen-2.1 harmonise gives a convincing shadow but redraws the picture ([relocate-harmonise.md](relocate-harmonise.md)) |
| Qwen Lightning | **Candidate to drop** | no object layers on the fox scene at 384, 512 or 640 px; story composites not improved |
| SDXL-inpaint amodal fill | **Park**; Qwen-2.1 replaces it | two good cottage fills; redundant with Qwen-2.1 extraction ([amodal-fill.md](amodal-fill.md)) |
| LayerD | **Park** | limited on painted scenes; CPU only ([../ideas-considered/models/layerd.md](../ideas-considered/models/layerd.md)) |
| ART+, LayerDiffuse-Flux, LayerDiffuse SDXL as a generator and its effect layers | **Dropped** | objects do not match the scene's style; effect layers gave objects or the scene itself ([../ideas-considered/](../ideas-considered/README.md)) |

## 3. What constrains the verdicts

1. **LayerDiffuse SDXL** has two roles: the engine of `relocate()`, and the layer-by-layer generator of the first prototype (replaced by "scene first, then split"). It is kept only for `relocate()` until a Qwen-2.1 based harmonise has been tested.
2. **Who gets credit for what:** the story edit (night, rain, a new element) is Qwen-2.1's; a splitter only splits the result; IC-Light, shadows and `relocate()` act on layers made by the splitter. Attribution per image: [provenance.md](provenance.md).
3. **Qwen-2.1 is the hub** (edit, image to image, add / remove / modify, background removal, amodal, relight; its output is what Stable-Layers splits), so its weaknesses matter most: about 24 s per call, a non-commercial licence, object position and scale not controlled in extraction. A second editor for the same roles is the main redundancy to consider.
4. **Memory:** the Qwen-2.1 profile alone loads about 21 GiB across the two T4s; SDXL-Turbo fits next to it with CPU offload (the `studio` profile). Stable-Layers needs the Qwen-Image-Layered transformer (12 GB or more), so it runs in a session of its own ([../guides/kaggle.md](../guides/kaggle.md)).
5. **IC-Light and the shadow layer** are independent of the other models (SD 1.5 and CPU), which makes them cheap to keep.

## 4. Combinations worth running end to end (open, [../todo.md](../todo.md))

| Combination | Models and roles | Open point |
|---|---|---|
| **A. Story editor (core)** | Qwen-2.1 edits the scene → Stable-Layers (640 px) or Qwen-2.1 splits the edit → per-layer Qwen-2.1 edit / IC-Light relight → shadow layers → recomposite | never run end to end; the split step is about 100 s |
| **B. Fast extraction** | Grounding DINO + SAM2 masks (3 s) → Qwen-2.1 for the background without the object and for hidden parts | pieces measured separately |
| **C. Box-controlled path** | RevealLayer (boxes, filled background) or CLD | slow; worth keeping only if box control is wanted in the frontend |

Licences: FLUX.1-dev (RevealLayer, CLD) and Qwen Research (Qwen-2.1) are non-commercial, Stable-Layers is under the Stability community licence; this is a personal non-commercial project, so all remain usable now ([TEMPLATE.md](TEMPLATE.md) lists the rest).
