# Research notes (sources behind the docs)

> **Role: source layer.** What was read, with citations, for the topics below. The conclusions and measurements are in `docs/` ([papers-survey](../docs/research/papers-survey.md), [models](../docs/models/README.md), [concepts](../docs/concepts/editing.md)); these notes keep the cited findings ("Takeaway" and "Cited Findings" per question) for follow-up work. They are dated snapshots (2026-11-07 to 11-09), condensed on 2026-11-11 to the facts the docs cite (about 50 KB from 147 KB), not kept up to date. Writing about unused models, the HCI and price surveys, platform terms and the long per-paper audits that the docs already summarise was removed on 2026-11-11 (git history, reference repository `layer-prototype`).

| Note | Topic | Used by |
|---|---|---|
| `Layered methods deep dive/joint_text_to_layers.md` | all methods: release status, code and weights, paper facts | [papers-survey](../docs/research/papers-survey.md) |
| `Layered methods deep dive/other_psd_methods.md` | methods we did not pursue (See-through, Alfie, Generative Omnimatte, TransPixar …) | [ideas considered](../docs/ideas-considered/README.md) |
| `Layered methods deep dive/spatial_edit_mechanics.md` | move / resize and re-harmonise: mechanics from LayerFusion, DreamLayer, PSDiffusion | [editing](../docs/concepts/editing.md), [relocate-harmonise](../docs/models/relocate-harmonise.md) |
| `Coherent layered generation pipeline/qwen_layered_and_layerdiffuse_papers.md` | how Qwen-Image-Layered and LayerDiffuse build coherent layers | [qwen-image-layered](../docs/models/qwen-image-layered.md) |
| `Layered loop open paths/qwen_image_21_rgba.md` | Qwen-Image-2.1: RGBA design, prompts, quality limits, T4 runs, licence | [qwen-image-2.1](../docs/models/qwen-image-2.1.md) |
| `Layered loop open paths/flux_layered_t4_and_weights.md` | FLUX-based layered models on fp16-only GPUs and where their weights come from | [fp16-on-t4](../docs/concepts/fp16-on-t4.md), [revealayer](../docs/models/revealayer.md), [cld](../docs/models/cld.md) |
| `Layered loop open paths/object_harmonisation.md` | harmonising a moved object: relighting, shadows, composite editors | [relocate-harmonise](../docs/models/relocate-harmonise.md), [relight-ic-light](../docs/models/relight-ic-light.md) |
| `Layered loop open paths/story_events_global_edits.md` | one event on every layer: weather, time of day, consistency methods | [editing](../docs/concepts/editing.md) |
| `Layered loop open paths/multi_turn_drift_evaluation.md` | measuring drift over many edits: benchmarks and metrics | [drift-evaluation](../docs/research/drift-evaluation.md) |
