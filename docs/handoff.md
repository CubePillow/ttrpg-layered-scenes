# Hand-off: first draft of the layer prototype (2026-11-11)

> **Role: start here if you are new to the project.** What the prototype is, what works today and what does not, how to run it, where things are in the code, what the evidence says about the models, and what to build next. Detail lives in the linked pages; this page does not repeat numbers it can link.

## 1. What this is

A free, non-commercial prototype for a storytelling game: **text prompt → coherent layered scene → edit single layers (re-prompt, move, resize) → recomposite → story events change the scene**. Hardware: a Windows laptop (CPU) and Kaggle (2× T4, fp16 only, 30 GPU-hours a week, at most two GPU sessions at once). No user study is planned; the prototype and its measurements are the result ([research/research-gap.md](research/research-gap.md)). Everything in this repo (code, experiments, research notes, decisions) is on GitHub: `github.com/CubePillow/ttrpg-layered-scenes` (the trimmed hand-off copy of `layer-prototype`).

## 2. State of the draft

| Part | State | Where |
|---|---|---|
| Local app (Gradio + a canvas editor, `prototype/app.py`) | **thin client, no model runs on the laptop**: Kaggle session panel (one Start / Stop for both models, status, idle clock, GPU memory), one page: picture (text, or a sketch / uploaded picture as image to image, 1-4 versions), split (Qwen-Image-2.1 or another splitter, versions per layer), layers row above the editor, **canvas editor** (rectangle and lasso select, move, resize, rotate, reorder, cut to a new layer, undo, export; composited in the browser, autosaved), Qwen-Image-2.1 layer edits with versions | [prototype/README.md](../prototype/README.md) |
| Kaggle session | profile **`studio`**: SDXL-Turbo (CPU offload) and Qwen-Image-2.1 in **one** session started by the app with the user's own Kaggle account (routes `/txt2img`, `/img2img`, `/decompose`, `/edit`, `/shutdown`); idle stop after 20 minutes, Stop in every state through ntfy; weights from attached Kaggle notebook outputs. **Run live 2026-11-11, works** (numbers in [status.md](status.md)). The earlier two-session setup (`sdxl-turbo`, `qwen21`) stays available as the fallback | `prototype/layerproto/{kaggle_launch,connection,remote_server,editor_api}.py`, `serve/{studio,launch,notebook,sdxl_turbo,qwen21}.py`, `ui/editor.html` |
| Other splitters | picked in the same page (Qwen-Image-Layered, Stable-Layers, Lightning, SAM2, RevealLayer, CLD); each starts its own Kaggle session on demand; built and benchmarked as profiles | [guides/kaggle.md §3b](guides/kaggle.md) |
| `relocate()` (LayerDiffuse SDXL re-harmonise) | works (3.4 s) as a `/chain/relocate` route of the optional chain server; **no longer a button in the app** | [models/relocate-harmonise.md](models/relocate-harmonise.md) |
| Shadow layers, IC-Light relight, story-event glue | code and tests exist (`shadow.py`, `relight.py`, `events.py`, `event_apply.py`); **not wired into the app**; the per-layer Qwen-2.1 edit (alpha check and retry) **is** | [models/shadow-layers.md](models/shadow-layers.md), [models/relight-ic-light.md](models/relight-ic-light.md) |
| Language model planner (Ollama) | **removed**; kept as a parked opt-in idea | [concepts/ollama-option.md](ideas-considered/ollama-option.md) |
| Progressive loading of layers | **not built** | [todo.md](todo.md) |

The CPU tests in `prototype/tools/test_*.py` pass (they use fakes, no GPU); the doc link check (`prototype/tools/check_doc_links.py`) reports no broken links.

## 3. The recommended core path

**SDXL-Turbo** makes the first picture (text, or a sketch / picture as image to image); **Qwen-Image-2.1** splits it and modifies it (scene edits for story events, per-layer edits and relights, hidden parts); Stable-Layers and CLD are optional splitters; IC-Light, shadow layers and `relocate()` act on single layers; RevealLayer is for inpainting; ART+, LayerDiffuse-Flux and LayerDiffuse SDXL as a generator are not pursued. The verdict per model with the reasons: [models/pipeline-plan.md](models/pipeline-plan.md); the architecture: [concepts/pipeline.md](concepts/pipeline.md). **Read [models/provenance.md](models/provenance.md) before trusting any picture in the model pages:** many strips chain models (SDXL-Turbo makes the scene, Qwen-2.1 edits it, a splitter splits it). The verdicts are the owner's; the pages report measurements.

## 4. Run it

### 4.1 The app (laptop, no model on it)

1. Install the packages once: `pip install -r prototype/requirements.txt`.
2. Put your Kaggle API token in `%USERPROFILE%\.kaggle` ([guides/kaggle.md §1](guides/kaggle.md)).
3. Weights once per Kaggle account (CPU session, no GPU quota), or attach the owner's public ones with `LAYERPROTO_WEIGHTS_OWNER`:
   ```bash
   python prototype/tools/make_weights_notebooks.py --owner <your-kaggle-user> --public --push
   ```
4. Start the app: `python prototype/app.py` (or `prototype\run_prototype.bat`), open http://127.0.0.1:7870.
5. **Kaggle session** panel: press **Start** (one session with SDXL-Turbo and Qwen-Image-2.1; the app pushes the notebook, finds the tunnel URL by itself and shows ✅ ready); then make the picture, split it and work on the layers. **Stop** when done (it also stops itself after 20 idle minutes; idle time counts against the weekly quota). Details: [prototype/README.md](../prototype/README.md).

### 4.2 Another splitter

Choose it in the **Splitter** dropdown of the page and press **Start this splitter's Kaggle session**; the app builds and pushes its notebook like the main one. To run any profile by hand, build its `serve` notebook and import it in the Kaggle editor: [guides/kaggle.md §3b](guides/kaggle.md).

### 4.3 Benchmarks, tests, docs

- A benchmark session for one profile (paths A and B on the fox & cottage scene): `make_profile_notebook.py --profile NAME --mode bench`, then push it with `python -m kaggle.cli kernels push -p .` from the notebook folder; the Kaggle CLI setup and rules are in [guides/kaggle.md](guides/kaggle.md). `prototype/tools/wait_and_fetch.sh` waits and downloads the outputs.
- Tests: every `prototype/tools/test_*.py` (fakes, no GPU); a live run through the real launcher: `prototype/tools/live_check.py`.
- After a measured run: add a row to `prototype/kaggle/benchmarks.csv`, run `python prototype/tools/build_benchmarks.py`, then `python prototype/tools/check_doc_links.py` before pushing. Add the image chain to [models/provenance.md](models/provenance.md).

## 5. Where things are in the code

| Path | What |
|---|---|
| `prototype/app.py`, `prototype/ui/editor.html`, `layerproto/editor_api.py` | the Gradio page (Kaggle session, picture, split, layers) and the canvas layer editor with its routes |
| `prototype/layerproto/engine.py` | the loop: first picture, split, edit layer, transform, fit to box, compose |
| `prototype/layerproto/{connection,kaggle_launch}.py` | where the two servers are (URL + token, re-read at every request); start / find / stop them with the Kaggle API and ntfy |
| `prototype/layerproto/backends/` | contracts and clients: `client` (txt2img, img2img, edit), `decomposer` (`DecomposeParams`, `RemoteDecomposer`, `MethodRouter`), `sam2_decomposer`, `qwen21_decomposer`; server-side only: `layerdiffuse_chain`, `chain_base`, `remote_chain` |
| `prototype/layerproto/serve/` | one module per Kaggle profile (`studio` = SDXL-Turbo + Qwen-Image-2.1, `sdxl_turbo`, `qwen21`, `qwen_layered`, `sam2`, `reveallayer`, `cld`, `artplus`), `profiles.py` (registry and the benchmark cases), `notebook.py` (builds the notebook), `launch.py` (tunnel, announce, idle stop), `benchmark.py` |
| `prototype/layerproto/remote_server.py` | FastAPI: `/health`, `/methods`, `/decompose`, `/edit`, `/txt2img`, `/img2img`, `/shutdown`, `/chain/*` |
| `prototype/layerproto/{shadow,relight,layer_edit,matte_fix,events,event_apply,fp16_mixed}.py` | shadow layers, IC-Light, alpha retry, halo fix, story events, the fp16 fix for T4 |
| `prototype/tools/` | the pipeline (`make_profile_notebook.py`, `make_weights_notebooks.py`, `live_check.py`, `build_benchmarks.py`, `check_doc_links.py`), the tests (`test_*.py`) and the local-model smoke scripts; the one-off experiment scripts the model pages mention were removed (git history, reference repository) |
| `prototype/kaggle/` | the benchmark table (`benchmarks.csv`), small result files and the inputs some scripts read; raw outputs were removed ([prototype/kaggle/README.md](../prototype/kaggle/README.md)) |
| `docs/` | state, plan, models, concepts, guides, history ([../README.md](../README.md)) |

## 6. What to build next

The open work, in order, is in [todo.md](todo.md): progressive loading of layers (the owner's design: work on the SDXL-Turbo baseline or the first Qwen-2.1 layer while the rest arrives), wiring the rest of the loop into the page (whole-scene story edits, shadows, the event router), an edit-success check, and the open experiments. A cold start of the Qwen session is about 7 minutes of loading plus a variable Kaggle start-up (up to 12 minutes seen), so keeping the session up during work and streaming layers matter more than shaving the load.

## 7. Known problems and cautions

- **Qwen-Image-Layered is inconsistent**: good on the forest scene, no object layers on the fox & cottage scene at 384, 512 or 640 px; the Stable-Layers LoRA on the same weights split it cleanly at 640 px ([models/qwen-image-layered.md](models/qwen-image-layered.md), [models/stable-layers.md](models/stable-layers.md)).
- **Qwen-2.1 extraction** leaves objects in the background layer on night and rain pictures, can invent a misplaced object (a stone dome instead of the small arch) and ignores boxes for position ([models/qwen-image-2.1.md](models/qwen-image-2.1.md)). Every call re-renders pixels slightly; a whole-scene edit redraws the whole picture (about 31 dB against the input even when told to change nothing).
- **Time:** only SAM2 meets the 30 s live-demo target by itself; Qwen-2.1 is about 24 s per call, Stable-Layers about 100 s at 640 px.
- **Licences:** FLUX.1-dev (RevealLayer, CLD, ART+, LayerDiffuse-Flux) and Qwen-Image-2.1 are non-commercial; Stable-Layers has Stability's community licence. This is a personal non-commercial project; check before any other use.
- **Secrets:** the tunnel tokens (`~/.layerproto/connection.json`), the ntfy topic (`~/.layerproto/launcher.json`) and the Kaggle token (`~/.kaggle`) never go into the repo. A pushed serve notebook contains its own token and topic and is private; do not make it public.
- **Kaggle:** the weekly quota is shown in the editor; a session stuck on "Starting" can still be running (stop it from the Active Events panel); notebooks of about 1.1 MB or more are rejected by the API; every trial has a 25-55 minute time cap ([guides/kaggle.md](guides/kaggle.md)).
- **Windows:** `run_prototype.bat` uses `fastsdcpu\env` when it exists and `python` otherwise; the paths in the scripts assume this repository's layout.
