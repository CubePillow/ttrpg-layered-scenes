# Ideas considered, not used (kept so nobody investigates them twice)

> **Role: parked investigations.** Everything here was tried, researched or planned and is **not** part of the current path ([../models/pipeline-plan.md](../models/pipeline-plan.md), [../status.md](../status.md)). Pages are kept whole, with their numbers and images, so a result is never redone by accident. The verdicts are the project owner's. Before starting an investigation, search here.

| Page | What it is | Why it is parked |
|---|---|---|
| [models/art-plus.md](models/art-plus.md) | ART+ (anonymous region transformer, FLUX LoRAs): layers from a caption and boxes | not pursued (owner): style and scale clash when pasted on another background, slow at 1024 px |
| [models/layerdiffuse-flux.md](models/layerdiffuse-flux.md) | LayerDiffuse on FLUX (RGBA objects per prompt) | not pursued (owner) |
| [models/layerd.md](models/layerd.md) | LayerD (Apache-2.0 layer decomposition for flat designs) | limited: peels one object with generic matting, painted scenes stay one layer |
| [models/layerdiffuse-sdxl.md](models/layerdiffuse-sdxl.md) | LayerDiffuse SDXL as a layer generator and its effect layers | generator and effect layers not pursued (owner); its engine is still used by `relocate()` ([../models/relocate-harmonise.md](../models/relocate-harmonise.md)) |
| [ollama-option.md](ollama-option.md) | a language model (Ollama / API) for prompt refinement, layer split, event routing | dropped from the app 2026-11-11; how to bring it back as an opt-in |
| [hosting-options.md](hosting-options.md) | API cost of Qwen-Image-Layered, university GPUs (LMU / LRZ), hosted image APIs and prices (2026-11-05), free browser generators | the project runs on free Kaggle GPUs |

Also parked, and still in their original places: Qwen-Lightning (tested, not recommended, [../models/qwen-lightning.md](../models/qwen-lightning.md)), the research notes ([../../research_notes/README.md](../../research_notes/README.md)), and the project history ([../log.md](../log.md)). The scripts that produced the parked results (ART+, LayerD, LayerDiffuse-Flux notebook generators), the raw result folders of superseded runs and the research notes about unused models were removed from this repository; the full set is in the untouched reference repository `github.com/MarkAndreDuesing/layer-prototype`.
