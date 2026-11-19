# Running models on free Kaggle GPUs

> **Role: guide (medium).** Step by step: set up the CLI once, let the app start its sessions, or build and run any model profile by hand. Why the fp16 patch is needed: [../concepts/fp16-on-t4.md](../concepts/fp16-on-t4.md). Settings and results per model: [../models/](../models/README.md).

## Public links

| What | Link |
|---|---|
| Code | https://github.com/CubePillow/ttrpg-layered-scenes |
| Cached weights (attach as notebook inputs) | `qwen-layered-weights-transformer` (Q4_K_S GGUF, 12.4 GB) and `qwen-layered-weights-base` (text encoder, VAE, configs, 16.9 GB) under https://www.kaggle.com/markandreduesing; `weights-qwen21-text-encoder` (17.5 GB), `weights-qwen21-parts` (5.3 GB), `weights-sdxl-turbo` (6.9 GB) |

## 1. One-time setup

1. Install the Kaggle CLI in its own venv:
   ```bash
   python -m venv kagglecli
   ```
   ```bash
   kagglecli\Scripts\pip install kaggle
   ```
2. Create an API token at https://www.kaggle.com/settings (API → Create New Token) and save it as `%USERPROFILE%\.kaggle\kaggle.json`. Phone-verify the account (needed for GPU and internet).
3. Weights: use the public weight notebooks above, or build your own once (CPU session, no GPU quota, each output under Kaggle's 20 GB limit):
   ```bash
   python prototype/tools/make_weights_notebooks.py --owner <you> --public --push
   ```
   Without attached weights a server downloads from Hugging Face at every start (17.5 GB for Qwen-2.1).

## 2. The normal way: the app starts and stops the session

The page's **Kaggle session** panel pushes the `studio` profile (SDXL-Turbo with CPU offload next to Qwen-Image-2.1) to your account, finds the tunnel URL through ntfy.sh, and stops it again (`/shutdown`; the session also ends after 20 idle minutes or the 3 h limit). Separate sessions per model are under **Separate sessions**. Details: [../../prototype/README.md](../../prototype/README.md).

## 3. Other profiles by hand

Each Kaggle session loads one model family (a *profile*, [`serve/profiles.py`](../../prototype/layerproto/serve/profiles.py)): `studio`, `sdxl-turbo`, `qwen21` (`qwen21-extract`, `/edit`), `qwen-layered` (methods `qwen-layered`, `stable-layers`, `qwen-lightning`; `-640` variant), `sam2` (`sam2-lama` with Grounding DINO, LaMa, optional SDXL-inpaint fill), `reveallayer`, `cld`, `artplus`. Load times: SAM2 about 40 s, Qwen-2.1 about 240-390 s, Qwen-Image-Layered about 350 s, FLUX-based ones 240-300 s.

1. Build the notebook:
   ```bash
   python prototype/tools/make_profile_notebook.py --profile sam2 --mode serve --owner <your-kaggle-user>
   ```
   Output: `prototype/kaggle/upload_profile_sam2_serve/profile-sam2-serve.ipynb` (git-ignored). `--mode bench` makes the benchmark notebook (paths A and B on the fox & cottage scene) that is pushed with the CLI; `prototype/tools/run_profile_batch.sh` waits for such sessions and downloads their outputs.
2. For a serve notebook, do not push it unless it should run now. By hand: Kaggle → New Notebook → File → Import Notebook → that file; Accelerator **GPU T4 x2**, Internet **On**; **Add Input** for the profile's weights notebooks (an imported notebook does not carry them).
3. Run all cells. The last prints `LAYERPROTO-CONNECT https://….trycloudflare.com|<token>`; the session ends itself after 20 idle minutes.
4. In the app, open **Separate sessions** and paste that line into the connect box (before or after the notebook). It is stored in `~/.layerproto/connection.json`, separate from `config.json`. The splitter dropdown chooses the method.
5. Stop the session when done (Stop in the app, or the idle stop).

CLI push, from inside the notebook folder (the CLI has a path bug otherwise):
```bash
cd prototype\kaggle\upload_profile_sam2_bench && python -m kaggle.cli kernels push -p .
```
```bash
python -m kaggle.cli kernels status <you>/profile-sam2-bench
```
```bash
python -m kaggle.cli kernels output <you>/profile-sam2-bench -p prototype/kaggle/results_profile_sam2
```
To record a run: add a row to `prototype/kaggle/benchmarks.csv`, run `python prototype/tools/build_benchmarks.py`, update the factsheet.

## 4. Gotchas

- **Qwen-Image-Layered:** reading the text encoder straight from `/kaggle/input` stalls at 0/729 tensors (copy to `/tmp` first, about 100 s; the SDXL weights likewise); the transformer is split over both T4s (blocks 0-29 / 30-59, peak 8.8 / 8.4 GB); T4 speeds: fp16 19 TFLOPS, bf16 2 (emulated), fp32 3.7.
- **Editor:** the Accelerator list offers only **GPU T4 x2**, **TPU v5e-8** and **None**; the quota line there (for example "15:05 / 30 hrs") is the live weekly GPU counter, and idle time counts. A session shown as "Draft Session Starting..." forever can still be running: clock icon at the bottom left (Active Events) → the session's **...** menu → **Stop Session**. Cell outputs sit in cross-origin iframes and can only be read from a screenshot.

## 5. Rules learned

| Rule | Why |
|---|---|
| `machine_shape: NvidiaTeslaT4` | gives 2× T4 |
| at most **2 batch GPU sessions** at once | a third push fails ("Maximum batch GPU session count of 2 reached"); CPU notebooks don't count |
| decode in fp32 with the big transformer offloaded first | fp32 VAE decodes of many layers ran out of memory next to the transformer (ART+, RevealLayer) |
| keep notebooks well under 1.5 MB | larger ones are rejected (HTTP 400): embed images as JPEG or attach data |
| 25-min SIGALRM cap in every trial | a stall still ends with a log; cancelled runs keep no output |
| check kaggle.com/work/code for an outage banner before re-pushing | the 2026-11-09 outage looked like account problems |
| smoke-test with 2 steps | GPU quota is 30 h/week |
| TPU via CLI (`TpuV5E8`) | stored, but batch runs got no TPU ([../research/hosting.md](../research/hosting.md#3-tpu)) |
