# Research gap and research questions: layered generation for an interactive story game

> **Role: research synthesis (current).** The gaps the prototype fills and the research questions it answers through the working loop and technical measurements (no user study). Checked 2026-11-09; [U] = not verified. The per-method comparison is [papers-survey.md](papers-survey.md); sources are in [research_notes](../../research_notes/README.md).

## 0. What our loop is

1. A prompt (or sketch) goes in and a picture is made.
2. The picture is split into a coherent RGBA layer stack.
3. The user edits single layers: re-prompt, move, resize.
4. The layers are recomposited.
5. A story event changes the scene ("the forest is now on fire").
6. Steps 3-5 repeat many times in one play session.

## 1. What the literature covers

- **Single-shot generation or decomposition**, evaluated once: Qwen-Image-Layered (Crello benchmark, RGB L1 and alpha IoU; a text-to-layers variant only qualitative), Stable-Layers, LayerDiffuse, LayerFusion, PSDiffusion, DreamLayer, OmniPSD, ART+, CLD, RevealLayer, LayerD, LASAGNA. Only DreamLayer has latent move / flip / resize with following shadows (IRH), and it has no code. LASAGNA has foreground-given-background generation with shadows and reflections, unreleased. LayerCraft (LLM agent, narrative demo, "code will be released") is conceptually closest to the loop but has no consistency evaluation.
- **Multi-turn editing benchmarks** (EdiVal-Agent, Omni IIE Bench, MSE-Bench, MTEdit, TailSteer; multi-turn consistent editing shows drift by about the 4th turn): all on **flat images**, never layer stacks ([drift-evaluation.md](drift-evaluation.md)).
- **Game and story work** (Narrative-to-Scene Generation, tile-based with temporal consistency as future work; Unbounded, flat images with regional IP-Adapter; MagicScroll, multi-layer scroll images for VR [U]): none uses RGBA layer stacks that persist across story events.
- Layered Diffusion Brushes (ICCV 2025) has a user study with artists, but its "layer" is an edit-parameter layer on one image.

## 2. The gaps

- **G1. No method evaluates layered scenes over long edit sequences.** The Qwen-Image-Layered paper asserts consistency is "fundamentally ensured" by the representation but has no metric, limitations section or repeated-edit experiment; "layers prevent drift" is untested.
- **G2. Story-event edits (global state changes) on a layer stack are unaddressed.** "The forest is on fire" must change background, trees, lighting and smoke coherently while characters stay fixed; LASAGNA does one conditional layer, LayerCraft object insertion, Qwen-Image-Layered edits a layer in isolation.
- **G3. Re-harmonisation after move / resize is not in any released model.** Qwen-Image-Layered treats moves as pixel operations, so shadows and lighting stay stale.
- **G4 (context only, not pursued; no user study is planned).** No HCI evaluation of layer-based generative scene editing for players or novices.
- **G5. Interactive latency on free hardware is unstudied.** Strong decomposers need 40-80 GB; the quality-latency trade-off at low steps and resolution, which is our setting, is unreported.

## 3. Research questions and what the prototype produced

- **RQ1: Do RGBA layer stacks reduce drift over long story-edit sequences compared with flat editing?** Answered technically with three arms (flat Qwen-2.1 edit, re-decompose every turn, persistent layers) and masked metrics: persistent layers keep the unedited area at about 60 dB, flat editing 14-20 dB, re-decomposing loses about 20 dB per cycle ([drift-evaluation.md](drift-evaluation.md)).
- **RQ2: How should a story event be routed to layers?** An LLM plan per event picks per-layer keep / relight / re-prompt / remove plus effects; four strategies were measured (`bg_relight`, `per_layer`, `recompose`, `effects`) and `recompose` (edit the whole composite with Qwen-2.1, then re-split) gave the best picture ([editing.md §3-5](../concepts/editing.md)). The router is library code; the local LLM was dropped ([ollama-option.md](../ideas-considered/ollama-option.md)).
- **RQ4: Can training-free re-harmonisation make moved layers plausible within an interactive budget?** `relocate()` does it in about 3.4 s per edit with a procedural shadow and optional IC-Light; Qwen-2.1 as a replacement is slower and less stable ([relocate-harmonise.md](../models/relocate-harmonise.md)).
- **RQ5: What is the latency-quality frontier of open layered models on free GPUs?** Measured per model: [models README](../models/README.md); the 30 s live budget is met only by SAM2 + LaMa, the 640 px Stable-Layers split takes about 100 s.

The niche is RQ1 + RQ2 + RQ4 together: a persistent RGBA stack, edited per layer and updated by routed story events with training-free re-harmonisation, on free hardware, shown by the working loop and technical measurements.

## 4. Does anything already do the whole loop?

No (as of 2026-11-09): nothing combines text to coherent layers, in-context per-layer regeneration, re-harmonised moves, event-driven multi-turn consistency and free-GPU latency. Qwen-Image-Layered plus an editor covers decompose, edit, recomposite with open weights, so the editing mechanics alone are not novel; the novelty is the loop (persistent layers, event routing, re-harmonised moves) and its technical evaluation, not a new generator or a user study. Unverified: the full Stable-Layers and RevealLayer papers, user studies inside the PSDiffusion / DreamLayer / LayerDiffuse papers, an exhaustive ACM DL search.
