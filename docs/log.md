# Log

> **Role: history.** The decisions and lessons of the project in date order, short. Every number and result lives in the page named at the end of each entry; the current state is [status.md](status.md), open work [todo.md](todo.md). Entries that only repeated those pages were cut on 2026-11-11 (the full diary is in git history and in the reference repository `layer-prototype`).

## 2026-11-05 to 07: research and the sketch-to-image phase

- **Quality bar and hosting.** Z-Image Turbo's level is enough; cost, accessibility and sketch input decide the model. Free recurring GPUs: Kaggle (about 30 GPU-h/week), the LMU CIP pool, Hugging Face Spaces; ruled out: SageMaker Studio Lab, Lightning AI, Comfy Cloud, Colab web UIs. → [research/hosting.md](research/hosting.md), [ideas-considered/hosting-options.md](ideas-considered/hosting-options.md).
- **Lesson:** the research-time CPU speed estimates (4-8 s per image) were 4-10× too optimistic; measured 20 s (SD-Turbo) and 58 s (SDXL-Turbo). They scaled published timings that used OpenVINO, the tiny decoder and 1 step. → [local-models/cpu-speedups.md](local-models/cpu-speedups.md).
- **Sketch to image on the CPU laptop** (FastSD CPU): SDXL-Turbo image to image on a filled sketch at Strength 0.8, 4 steps is the best path; ControlNet dropped. → [../experiments/README.md](../experiments/README.md), [local-models/fastsd-cpu/](local-models/fastsd-cpu/INSTALL.md).
- **First layered prototype** (LLM splits the prompt, one LayerDiffuse layer per noun, boxes): a sticker collage, not coherent layered generation. **Decision:** coherence has to come from one shared image: generate the scene, then split it. → [concepts/pipeline.md](concepts/pipeline.md).
- **Hosting decision:** free Colab forbids serving endpoints; Comfy Cloud is a proprietary paid UI; Kaggle is the free GPU route, Modal ($30/month credit, needs a card) the fallback.

## 2026-11-07 to 09: Qwen-Image-Layered on Kaggle's 2× T4

- **bf16 on an fp16 GPU.** Qwen-Image overflows fp16 and the T4 has no bf16; single-layer patches only moved the failure. The fix (`fp16_mixed`: scale every linear's input, fp32 residual stream) gave no NaNs. → [concepts/fp16-on-t4.md](concepts/fp16-on-t4.md).
- **Fitting it:** the 4-bit GGUF split over both T4s; decode one layer at a time with the transformer on the CPU; reading the base weights straight from `/kaggle/input` stalls (copy to `/tmp` first); the weights are cached as Kaggle notebook outputs. → [models/qwen-image-layered.md](models/qwen-image-layered.md), [guides/kaggle.md](guides/kaggle.md).
- **Speed.** One 640 px, 4-layer step is about 6.6 × 10¹⁴ FLOPs, about 35 s at the T4's 19 TFLOPS, so no software trick reaches 40 s at the defaults. Lower resolution, CFG 1 (halves the time) and 4-5 steps did: 384 px, 3-4 layers, 4 steps gives 27-35 s. The split carries over to pixel-art and sketch scenes; thin low-contrast subjects (a pale skeleton) can stay in the background. → benchmark table in [models/qwen-image-layered.md](models/qwen-image-layered.md).
- **Lightning LoRA:** no speed-up at 4 steps, lower fidelity, cleaner separation of thin subjects. → [models/qwen-lightning.md](models/qwen-lightning.md).
- **Kaggle lessons.** At most 2 batch GPU sessions; a 25-minute SIGALRM cap on every trial so a stall still ends with a log; smoke-test with 2 steps; check kaggle.com for an outage banner before re-pushing (the 2026-11-09 outage looked like account problems). → [guides/kaggle.md](guides/kaggle.md).

## 2026-11-09: other routes, move / resize, FLUX-class models

- **SAM2 + LaMa:** 3-7 s, fragments by "largest K masks", clean by noun with Grounding DINO boxes. **LayerD:** returned one layer on painted scenes (its matting network output exactly 0). → [models/sam2-lama.md](models/sam2-lama.md), [ideas-considered/models/layerd.md](ideas-considered/models/layerd.md).
- **`relocate()`** (training-free move / resize re-harmonisation on the LayerDiffuse chain, 4 s per edit): v1 (stochastic sampler) broke at strength 0.6; v2 (Euler, mask extraction) works; v3 / v4 pinning was a no-op (the pin mask used alpha > 128 eroded 12 px, about 42 of 4096 latent pixels); v5 fixed it. → [concepts/editing.md](concepts/editing.md), [models/relocate-harmonise.md](models/relocate-harmonise.md).
- **FLUX-class models on the T4:** plain FLUX.1-dev GGUF runs cleanly in fp16 (41 s for 16 steps); the noise from RevealLayer, ART+ and LayerDiffuse-Flux came from their own code (−1e9 attention masks, unguarded residuals, fp16 VAE decodes, a LoRA key mismatch, a loader that overwrote stacked LoRAs, a wrong `vae_scale_factor`). → [concepts/fp16-on-t4.md](concepts/fp16-on-t4.md), [revealayer](models/revealayer.md), [cld](models/cld.md), [ART+](ideas-considered/models/art-plus.md), [LayerDiffuse-Flux](ideas-considered/models/layerdiffuse-flux.md).
- **TPU probe:** three CLI runs never got a TPU; an interactive session sat at queue position 1510. → [research/hosting.md](research/hosting.md#3-tpu).

## 2026-11-10: the shared test scene, Qwen-Image-2.1, the editing experiments

- **Test scene:** the fox & cottage picture (SDXL-Turbo, seed 13, chosen by the owner) is the main input; the forest, pixel-art and sketch scenes stay as style checks. → [status.md](status.md).
- **Qwen-Image-2.1** (17-23 s per call): extraction, RGBA edit, night and heavy-rain scene edits that keep the composition, text to transparent object. → [models/qwen-image-2.1.md](models/qwen-image-2.1.md).
- **Story events:** whole-scene edit + re-split works; `bg_relight` (background edit + IC-Light) gives colour casts; per-layer Qwen-2.1 relight works where the alpha survives. **Drift:** persistent layers keep the unedited area at about 60 dB, flat Qwen-2.1 editing 14-20 dB (the fox duplicated), re-decomposing every turn loses about 20 dB per cycle. → [concepts/editing.md](concepts/editing.md), [research/drift-evaluation.md](research/drift-evaluation.md).

## 2026-11-11: assessment, plan and hand-off

- **Assessment:** Qwen-Image-Layered is inconsistent (good on the forest, no object layers on the fox scene); Stable-Layers at 640 px splits it cleanly; Qwen-2.1 extraction is clean on the daylight scene and weaker on the night and rain edits. **Core path:** SDXL-Turbo first picture, Qwen-Image-2.1 split and edits. → [models/pipeline-plan.md](models/pipeline-plan.md), [models/provenance.md](models/provenance.md) (which model made which part of every picture).
- **Prototype made a thin client:** all models run on Kaggle; the connection is kept apart from the settings (fixes the start-order bug); weights are attached as notebook outputs instead of downloaded at every start; the app starts and stops the sessions with the user's Kaggle account (URL through ntfy.sh, idle stop, Stop in every state); Ollama dropped. → [../prototype/README.md](../prototype/README.md), [ideas-considered/ollama-option.md](ideas-considered/ollama-option.md).
- **One shared session** (SDXL-Turbo with CPU offload next to Qwen-Image-2.1) and a new page with a sketch input, versions and a canvas layer editor; both run live. → [status.md](status.md).
- **Repository trimmed** for the team: raw outputs, one-off scripts and superseded notes removed; dropped models documented under [ideas-considered/](ideas-considered/README.md).
