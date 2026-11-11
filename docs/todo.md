# Open work

> **Role: current.** What is still to do, in one place. Finished work is recorded in [status.md](status.md) and the model pages; the decisions per model are in [models/pipeline-plan.md](models/pipeline-plan.md). The owner decides model verdicts; nothing is "rejected" here.

## Prototype (in this order)

- [ ] **Progressive loading of layers (the owner's design).** The user works on the SDXL-Turbo baseline, or on the first Qwen-2.1 layer, while the other layers and objects keep arriving. Qwen-2.1 costs about 24 s per object (118 s for four objects plus background; 139-184 s on the story composites), which is acceptable if layers stream in. Needs an async decompose route (a job id and `GET /jobs/<id>` returning the layers finished so far, or server-sent events) and a page that adds layers as they arrive, the background and the biggest object first. `Decomposer.decompose` returns all layers at once today.
- [ ] **Wire the rest of the loop into the page:** whole-scene story edits (Qwen-2.1 edit of the picture, then a split), `event_apply.py`, the event router (`events.py`; needs a planner, [ideas-considered/ollama-option.md](ideas-considered/ollama-option.md)) and the shadow layers (multiply option).
- [ ] **Edit-success check.** The alpha check accepts an edit whenever the transparency is right; "make the fox white" came back orange and was accepted. Add a colour or content check, or show the versions and let the user pick (versions exist).
- [ ] **Qwen-2.1 extraction:** pass the box (crop or paste back) so objects keep their place and scale (the arch came back too big); keep the cottage layer free of the tree; make background removal work on the night and rain edits.
- [ ] **SDXL-Turbo prompt style** that gives separable layouts (the draft pictures often contain a second fox, [models/sdxl-turbo.md](models/sdxl-turbo.md)).
- [ ] **Stop while a session is still starting:** works through the ntfy message; the Kaggle CLI itself has no cancel, so a session that is still queued ends only when it starts.
- [ ] **Not yet run live:** a splitter other than Qwen-Image-2.1 (starts its own session), "Versions per layer" above 1 for the split, loading a scene saved before rotation existed (defaults to 0).
- [ ] **Editor ideas:** opacity and blend modes per layer, feathered and magic-wand selections, copy a layer, keyboard nudging, a mask brush for refining a cut.
- [ ] **Re-harmonise after a move:** `relocate()` is a server route (LayerDiffuse chain profile) but no longer in the page; a Qwen-2.1 replacement is under Experiments.
- [ ] **Local-model scripts** that are kept as records (`make_test_scene.py`, `smoke_*.py`, `test_ic_hue.py`): port or delete them if the team wants a strictly local-model-free repo.

- [ ] **Box-first extraction (owner idea):** a one-shot model (VLM, or Grounding DINO + SAM2) proposes object boxes on the generated picture, the user edits them, and only then does Qwen-2.1 extract each layer, one on demand. Also removes the empty-names-box problem (Qwen-2.1 needs names; a name-free "extract the main subject" call is untested and gives one object per call).
- [ ] **Box-defined input:** a second input form next to the sketch where the user draws placement boxes, based on a noun breakdown of the prompt.
- [ ] **Prompt helper for SDXL-Turbo:** a template and, optionally, a hosted one-shot rewriter (opt-in, [ideas-considered/ollama-option.md](ideas-considered/ollama-option.md)). Known rules: the Turbo models read "pixel" as a texture, do not understand spatial language (only a sketch or ControlNet fixes layout), and CLIP ignores negation, so avoid "no" and "without" in the main prompt.
- [ ] **UI bug pass:** the page is buggy but does the baseline task; list the known glitches and fix them before the team demo.

## Product and design

- [ ] **Game-flow writeup** as flow-diagram text: a D&D session step by step and where the app comes in (the relation to the game is currently missing), then test it with the prototype.
- [ ] **Design decisions mapped to research gaps** ([research/research-gap.md](research/research-gap.md)); a rule of thumb, not 5-6 gaps per decision. Name the target audience.
- [ ] **Team deployment options:** a container image, Kubernetes, or Kaggle-only (the app is already a thin client); what else would let the team use it consistently.

## Experiments

- [ ] **Qwen-2.1 harmonise with a lighting mismatch** (the fox moved from sun to shade, or into the night scene), per layer instead of a whole-scene edit; replaces `relocate()`'s LayerDiffuse SDXL engine if it holds up ([models/relocate-harmonise.md](models/relocate-harmonise.md)).
- [ ] **IC-Light tuning (kept):** a stronger rain pre-grade, other prompts and step counts, `restore_chroma` on the night and rain variants, the arch layer that turns cyan, a lighting mismatch inside one scene; compare with the Qwen-2.1 per-layer relight on the same layers ([models/relight-ic-light.md](models/relight-ic-light.md)).
- [ ] **Qwen-Image-Layered (in contention):** more scenes; a full-precision run (hosted API, about $0.05) to separate "our Q4 GGUF + fp16" from "the model"; what it can do that Qwen-2.1 extraction cannot (all layers in one pass).
- [ ] **Stable-Layers:** other scenes (forest, pixel art, sketch) and 2-3 steps at 640 px (a step closer to 30 s); the same for CLD.
- [ ] **SAM2 masks + Qwen-2.1 fill** (combination B in [models/pipeline-plan.md](models/pipeline-plan.md)) against Qwen-2.1 extraction alone.
- [ ] **Combined run:** combination A end to end on the fox & cottage scene and two more, with the model and role named for every output.
- [ ] **Image to image:** compare Qwen-2.1 with other image-to-image models; test Qwen-2.1 transparent effect layers (fog, glow, snow); decide Lightning (candidate to drop).
- [ ] **Drift:** more scenes, re-prompt and relight edits ([research/drift-evaluation.md](research/drift-evaluation.md)).
- [ ] **Not looked at yet:** LayerFusion (training-free attention blending), the DreamLayer dataset (a possible fine-tune for move / resize), further editing and segmentation models as alternatives to Qwen-2.1 and SAM2, other relighting models than IC-Light v1, layered models released after 2026-11-09 ([research/papers-survey.md](research/papers-survey.md)).
- [ ] **Equal-time benchmark:** every splitter at the same compute budget (about 30 s and about 3 min); RevealLayer and CLD are still measured at far longer budgets.
- [ ] **Verify that gap G1 is really open** (layer stacks over a long edit timeline) against recent multi-turn layered papers; it is the strongest justification for the layered approach.
- [ ] **Word and relation breakdown with a caption check:** it did nothing and was removed with Ollama; read how the papers used it and decide whether it comes back.
- [ ] **Image-to-layers first segmenter:** a quickly made decent starting picture (SDXL-Turbo) for Qwen-Image-Layered or Stable-Layers to split, instead of generating from scratch.
- [ ] **TPU:** an interactive session sat at queue position 1510 and no probe ran ([research/hosting.md](research/hosting.md#3-tpu)); retry when quiet or skip.

## Documentation

- [ ] Keep [status.md](status.md) and the factsheets in sync after each run; add a row to `prototype/kaggle/benchmarks.csv` and run `python prototype/tools/build_benchmarks.py`; run `python prototype/tools/check_doc_links.py` before pushing.
