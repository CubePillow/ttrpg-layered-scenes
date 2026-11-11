# Running models on the laptop (kept as an option; the app no longer does it)

> **Role: reference for local runs.** The app is a thin client and every model runs on Kaggle GPUs ([../../prototype/README.md](../../prototype/README.md)). The material here records how the models were run on a CPU laptop (Windows, Core 7 150U, about 11 GB free RAM) in case the project moves back to local or hybrid use.

| What | Where | Notes |
|---|---|---|
| FastSD CPU (SDXL-Turbo and LCM on the CPU, sketch-to-image) | [fastsd-cpu/INSTALL.md](fastsd-cpu/INSTALL.md), [fastsd-cpu/USAGE.md](fastsd-cpu/USAGE.md), patch and offline start in `../../fastsdcpu_local/` | the earlier sketch-to-image phase: about 58-70 s per 512 px SDXL-Turbo image, 4 steps |
| CPU speed-ups | [cpu-speedups.md](cpu-speedups.md) | measured and proposed levers |
| Sketch-to-image findings (local models) | [../../experiments/README.md](../../experiments/README.md) | three final sheets, the sketch inputs and the scripts that drive FastSD CPU |
| Scripts that load a model locally | `../../prototype/tools/make_test_scene.py` (SDXL-Turbo test scene), `smoke_layerdiffuse.py`, `smoke_chain.py`, `test_ic_hue.py` (IC-Light relight, about 40 s per layer on the CPU) | the layer library for them (`layerproto/relight.py`, `shadow.py`, `backends/layerdiffuse_chain.py`) is kept; LayerDiffuse needs the code from [../../prototype/vendor/README.md](../../prototype/vendor/README.md) |
| The earlier local app (language-model planner with Ollama, LayerDiffuse chain on the CPU, 11 GB RAM) | git history before commit "Thin client" (2026-11-11), the planner idea in [../ideas-considered/ollama-option.md](../ideas-considered/ollama-option.md) | about 80 s per layer on this CPU |
