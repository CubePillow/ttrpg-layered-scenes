# Layer scene prototype (hand-off state 2026-11-11)

A thin local app for the loop *prompt or sketch → picture → layers → edit layers → recomposite*. **No model runs on your computer**: the models run in one Kaggle GPU session that the app starts and stops for you with your own Kaggle account. Read [../docs/handoff.md](../docs/handoff.md) first for the project, the evidence and what to build next.

| Part of the session | Model | Does |
|---|---|---|
| SDXL-Turbo (CPU offload, profile `studio`) | SDXL-Turbo | picture from text, or from a sketch / uploaded picture (image to image); several versions; 6-8 s per picture in the shared session |
| Qwen-Image-2.1 | Qwen-Image-2.1 | split a picture into background + one RGBA layer per object; edit one layer (several versions) |

Both models live in **one** Kaggle session (profile `studio`): one Start, one idle clock, one session of quota. Measured on the two T4s: after loading, GPU 0 has 8.8 GiB free and SDXL-Turbo, which visits GPU 0 part by part, still works after Qwen has split and edited ([../docs/status.md](../docs/status.md)). Other splitters (Qwen-Image-Layered, Stable-Layers, Qwen-Lightning, SAM2 + Grounding DINO + LaMa, RevealLayer, CLD) are picked in the same page; each runs in a Kaggle session of its own that the page starts on demand.

## Set it up once (about 10 minutes)

1. Install the app's few packages (Python 3.10+):
   ```bash
   pip install -r prototype/requirements.txt
   ```
   (If `python -m kaggle.cli --version` complains about `six`, also run `pip install six`.)
2. Give the app your Kaggle account: create an API token at https://www.kaggle.com/settings (API) and save it as `%USERPROFILE%\.kaggle\kaggle.json` (or the new `access_token` file). The account must be phone-verified (needed for GPU and internet).
3. Weights: the session reads the model files from attached Kaggle notebook outputs instead of downloading them at every start (Qwen-Image-2.1 alone is 22.8 GB). By default it attaches the public weight notebooks of `markandreduesing` (`weights-qwen21-text-encoder`, `weights-qwen21-parts`, `weights-sdxl-turbo`); to use another owner set `LAYERPROTO_WEIGHTS_OWNER=<their user name>`, or build your own once (a CPU session, **no GPU quota**):
   ```bash
   python prototype/tools/make_weights_notebooks.py --owner <your-kaggle-user> --public --push
   ```
   Wait until the three notebooks show *Complete* on kaggle.com/code.

## Run it

1. Start the app: double-click `prototype\run_prototype.bat` or run
   ```bash
   python prototype/app.py
   ```
   and open http://127.0.0.1:7870 (`LAYERPROTO_PORT` changes the port).
2. **Kaggle session:** press **Start**. The app pushes the notebook to your Kaggle account, shows *starting* with the Kaggle status and turns to ✅ *ready* by itself (about 5 minutes of loading plus Kaggle's own start-up, up to 20 more minutes when Kaggle has a queue). The panel then shows the idle clock and the free GPU memory. **Stop** ends the session in every state, also while it is still loading.
3. **1. The picture:** describe the scene and press *Make the picture from the text*, or draw a sketch (or upload a picture and draw on it), set the strength and press *Make the picture from the sketch*. *Versions* makes 1-4 pictures with consecutive seeds; click one to use it, or upload your own picture on the right.
4. **2. Split into layers:** choose the splitter (Qwen-Image-2.1 is the default and needs the objects named, back to front, e.g. `cottage, big tree, red fox`), optionally *Versions per layer* (the split is repeated with other seeds and each layer gets one variant per run), press **Split**. Inputs that a splitter does not use are hidden. For a splitter other than Qwen-Image-2.1 press *Start this splitter's Kaggle session* first and wait for ✅.
5. **3. Work on the layers:** the *All layers* and *Variants* rows are above the editor; the variants row follows the layer you pick in the editor (click a variant to switch the layer to it). The **editor** works like Krita / GIMP: *Move* drags the layer under the pointer (or the picked one), corner handles resize, the round handle rotates; *Rectangle* and *Lasso* select an area of the picked layer, then drag inside the selection to move just that part (it becomes a new layer) or use *Cut to new layer* / *Erase selection*; the layer list shows / hides, reorders and deletes layers; *Undo* (Ctrl+Z), *Reset layer*, *Export PNG*. The picture is composited in the browser, so moving never reloads it, and every change is saved as you go. **Edit the picked layer** (Qwen-Image-2.1, about 25 s per version) adds variants to the layer you picked in the editor.
6. Scenes are saved in `prototype/scenes/<id>/` (load one with the dropdown). **Stop** the session when you are done; it also stops itself after 20 idle minutes (`idle_minutes` in `config.json`). Idle time counts against your weekly Kaggle quota like any other running time.

## How the pieces find each other

- The app builds the serve notebook for the profile (`layerproto/serve/notebook.py`) with a fresh random token and a private random topic, pushes it with the Kaggle API (`layerproto/kaggle_launch.py`) and waits.
- The notebook loads the models, opens a Cloudflare quick tunnel, prints a `LAYERPROTO-CONNECT` line and posts the tunnel URL to https://ntfy.sh/<your topic>. The topic is a long random secret kept in `~/.layerproto/launcher.json`. **The token is never sent through ntfy**: the app wrote it into the (private) notebook, so the URL alone is useless. ntfy.sh is a public relay service run by a third party; the only thing it sees is a short-lived tunnel URL.
- **Stop** also goes through the same topic (`{"stop": run id}`): a watcher thread in the notebook ends the session within about 15 seconds, also during loading. A running server additionally gets `POST /shutdown`.
- The app stores each server's URL and token in `~/.layerproto/connection.json` (written atomically, separate from `config.json`) and re-reads it at every request, so the start order never matters.
- If ntfy.sh is blocked on your network the app cannot find the session; set `LAYERPROTO_GEN_URL` / `LAYERPROTO_GEN_TOKEN` and `LAYERPROTO_URL` / `LAYERPROTO_TOKEN` from the line the notebook prints (see `layerproto/connection.py`).

## Files

- `app.py`: Gradio UI (Kaggle session, picture, split, layers + editor) and the FastAPI routes of the editor.
- `ui/editor.html`: the canvas layer editor (plain HTML + JavaScript, no build step). `layerproto/editor_api.py`: its routes (`/editor`, `/api/scene/<id>`, `.../save`, `.../selected`, `/scenes/<id>/<file>`).
- `layerproto/engine.py`: pictures (versions), split (versions), edit one layer (versions), editor state, compose with move / resize / rotate.
- `layerproto/connection.py`, `kaggle_launch.py`: where the servers are; start / find / stop them.
- `layerproto/backends/client.py`, `backends/decomposer.py`: calls to the servers.
- `layerproto/remote_server.py`: the server (`/health`, `/txt2img`, `/img2img`, `/decompose`, `/edit`, `/shutdown`, idle clock).
- `layerproto/serve/`: one module per profile (`studio` = SDXL-Turbo + Qwen-Image-2.1), `profiles.py` (registry and benchmark cases), `notebook.py` (notebook builder), `launch.py` (runs in the notebook: tunnel, announce, idle stop), `benchmark.py`.
- `tools/`: the pipeline scripts (`make_profile_notebook.py`, `make_weights_notebooks.py`, `live_check.py`, `build_benchmarks.py`, `check_doc_links.py`), the tests (`test_*.py`, all run without a GPU) and a few local-model smoke scripts (`make_test_scene.py`, `smoke_*.py`, `test_ic_hue.py`); the app itself never loads a model.
- `vendor/`: the LayerDiffuse SDXL port, used only by the optional chain profile on a GPU server.

## Settings

`config.json` (git-ignored, optional) overrides the defaults in `layerproto/config.py`: `width`/`height` (512), `first_steps` (SDXL-Turbo steps, 4), `first_seed`, `idle_minutes` (20). The connection is not a setting.

An optional local LLM for prompt refinement and layer splitting (Ollama) was dropped from the app: [../docs/ideas-considered/ollama-option.md](../docs/ideas-considered/ollama-option.md).
