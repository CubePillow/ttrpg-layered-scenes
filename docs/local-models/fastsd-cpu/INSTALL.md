# FastSD CPU: Install and Offline Setup

Copy of the team's shared doc (https://claude.ai/artifact/Ed34AvmQ9odLFHVzZnga8L), synced 2026-11-09. How to use it: [USAGE.md](USAGE.md). The local patch and launcher are also in [../../fastsdcpu_local/](../../../fastsdcpu_local).

## Step 0: What we are doing and why

**The goal:** generate images on an ordinary laptop or desktop CPU, with no graphics card, and keep working with no internet connection after a one-time setup. Two ways of generating are covered:

- **Text to Image:** you describe a picture in words.
- **Image to Image:** you give a starting image (for example a rough sketch) plus a description, and the model redraws it.

**Why this setup:**

- The models used here are "turbo" models that need only 4 steps per image, which makes CPU-only generation take tens of seconds instead of many minutes.
- Everything runs locally, so prompts and images stay on your machine and the tool works without a connection.
- We use [FastSD CPU](https://github.com/rupeshs/fastsdcpu), an existing open-source project, instead of building our own pipeline, so setup follows its published instructions.

**The two paths.** A path is one model. Set up only the ones you need:

| Path | Model | Use it for | Disk | Free RAM while running |
| --- | --- | --- | --- | --- |
| 1 | `stabilityai/sd-turbo` (SD-Turbo) | Faster results, about 20 s per image | 4.9 GB | about half of Path 2 |
| 2 | `stabilityai/sdxl-turbo` (SDXL-Turbo) | Best results, about 58 s per image | 13 GB | about 11 GB |

Times and RAM were measured on a CPU-only laptop with 15.7 GB RAM at 512 x 512. Close other large programs before running Path 2.

**Licence note:** the FastSD CPU README states that the SD Turbo and SDXL Turbo models are intended for research purposes only. Check the model licences on Hugging Face before using results beyond the prototype.

## Known problems on Windows machines (read before starting)

- **Smart App Control / Application Control** blocks unsigned native files. The error "blocked by Application Control" names the file; `scikit-learn` had to be uninstalled from the `env` for this reason (only `nncf` wants it). Deal with the file the error names, then retry.
- **RAM.** Silent crashes or `MemoryError` mean low free RAM (browser, IDE, virtual machines). SDXL-Turbo needs about 11 GB free, so close everything else first.
- **Downloads.** Set `HF_HUB_DISABLE_XET=1` for model downloads (the xet downloader ran out of memory). For offline use keep the models in `fastsdcpu/models/` (the Hugging Face cache fails offline with `IncompleteSnapshotError`).
- **Local patch.** `src/backend/lcm_text_to_image.py` casts pipeline components to float32 on the CPU (fixes the SDXL-Turbo "Half and Float" error with transformers 5); a `git pull` overwrites it, so keep the copy in `fastsdcpu_local/`.

## What FastSD CPU is and how this guide is organised

**The repository.** [rupeshs/fastsdcpu](https://github.com/rupeshs/fastsdcpu) is an open-source project described in its README as a faster version of Stable Diffusion on CPU. It builds on Latent Consistency Models, Adversarial Diffusion Distillation and distilled few-step models. It offers three interfaces:

- a desktop GUI for basic text to image,
- a **web UI** with the advanced features, including image to image,
- a command-line interface.

This guide uses the web UI, which opens in your browser at http://127.0.0.1:7860 and runs entirely on your own machine. FastSD CPU supports Windows, Linux and Mac; this guide covers Windows. The upstream instructions are in the README's [Installation](https://github.com/rupeshs/fastsdcpu#installation) section, and Part A follows them.

**What gets set up, in order:**

1. Python and uv, the tools FastSD CPU installs with.
2. FastSD CPU itself, in its own `env` folder.
3. One folder of model files per path, stored in `fastsdcpu\models`.
4. A start script that runs the app in offline mode.

**How this guide is organised:**

- **Part A: Common setup.** Steps 1 to 3, done once per machine, with internet.
- **Part B: Path 1 setup (SD-Turbo).** Complete on its own after Part A.
- **Part C: Path 2 setup (SDXL-Turbo).** Complete on its own after Part A. You do not need Part B for it.
- **Part D: Another machine.** Reuse the downloaded models on a second computer.

Internet is needed for Part A and for the model downloads in Parts B and C. Nothing needs internet after that.

## Requirements

Check these before starting.

### Hardware

| Item | Requirement | Tested on |
| --- | --- | --- |
| Processor | Any modern 64-bit CPU. No graphics card needed. | Intel Core 7 150U laptop |
| RAM | Path 1: about half of Path 2. Path 2: about 11 GB free while generating, so 16 GB total is recommended. The FastSD CPU README lists 2 GB as the minimum for its LCM mode. | 15.7 GB |
| Free disk | About 1 GB for the install, plus 4.9 GB for Path 1 and 13 GB for Path 2. | 238 GB free |

### Software

| Item | Requirement | Used in this guide |
| --- | --- | --- |
| Operating system | Windows 10 or 11, 64-bit | Windows 11 Pro |
| [Python](https://www.python.org/downloads/) | 3.10 or higher (upstream requirement) | 3.11.9 |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Required by `install.bat` (upstream requirement) | 0.13.7 |
| [Git](https://git-scm.com/download/win) | Optional. You can download a release zip instead. | 2.45.1 |
| PyTorch (CPU build) | Installed by `install.bat` | 2.8.0+cpu |
| Web browser | Any current browser, to open the web UI | n/a |

### Network

- Internet is needed once for Part A and for the model downloads in Parts B and C.
- After that the app runs with no connection.

## Part A: Common setup (once per machine, online)

You need Windows 10 or 11 (64-bit), an internet connection for this part, and about 1 GB of free disk for the install itself (models are extra, see Step 0).

### A1. Install the tools and FastSD CPU

This follows the [upstream installation instructions](https://github.com/rupeshs/fastsdcpu#installation).

**A1.1** Install Python 3.10 or higher from [python.org](https://www.python.org/downloads/). Tick "Add python.exe to PATH" in the installer.

**A1.2** Install uv in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**A1.3** Open a new PowerShell window and check both tools:

```powershell
python --version
uv --version
```

**A1.4** Get the code, either by cloning the repo with [Git](https://git-scm.com/download/win):

```powershell
git clone https://github.com/rupeshs/fastsdcpu.git
cd fastsdcpu
```

or by downloading and unzipping a [release](https://github.com/rupeshs/fastsdcpu/releases).

**A1.5** Double-click `install.bat` in the `fastsdcpu` folder (or run `.\install.bat` in PowerShell). It creates the `env` folder and downloads all packages, which takes a while. Wait for "FastSD CPU env installation completed."

### A2. Check the torch version

**A2.1** In PowerShell, in the `fastsdcpu` folder:

```powershell
env\Scripts\python.exe -c "import torch; print(torch.__version__)"
```

The settings in the usage guide were tested with `2.8.0+cpu`, the version `install.bat` installs first.

**A2.2** If it prints a different version, reinstall the tested one:

```powershell
uv pip install --python env\Scripts\python.exe torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu --reinstall-package torch --reinstall-package torchvision --no-deps
```

### A3. Prepare offline mode

The app's **Use locally cached model or downloaded model folder(offline)** setting makes it load models from local files only (see the upstream [offline instructions](https://github.com/rupeshs/fastsdcpu#how-to-use-lcm-lora-models-offline)). The extra variables below stop the Hugging Face and Gradio libraries from contacting the internet at all.

**A3.1** Open `configs\settings.yaml`, change this line and save the file:

```yaml
use_offline_model: true
```

**A3.2** In the `fastsdcpu` folder, create a file named `start-webui-offline.bat` with this content (a copy is in [../../fastsdcpu_local/start-webui-offline.bat](../../../fastsdcpu_local/start-webui-offline.bat)):

```bat
@echo off
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set GRADIO_ANALYTICS_ENABLED=False
set PATH=%PATH%;%~dp0env\Lib\site-packages\openvino\libs
call "%~dp0env\Scripts\activate.bat" && python "%~dp0src\app.py" -w
```

**A3.3** From now on, start the app by double-clicking `start-webui-offline.bat`, not `start-webui.bat`. Start it from the `fastsdcpu` folder so the relative `models/...` paths used below resolve. To stop it, click its terminal window and press `Ctrl+C`.

Part A is finished. Continue with Part B (Path 1), Part C (Path 2), or both.

## Part B: Path 1 setup (SD-Turbo)

Requires Part A. Does not require Part C.

### B1. Download the model (online, about 4.9 GB)

Offline mode needs complete model files in a folder. The app's own automatic download is not enough: its cache holds only the files the app used, and offline mode then fails with `IncompleteSnapshotError`. A local model folder avoids that.

**B1.1** In PowerShell, in the `fastsdcpu` folder:

```powershell
env\Scripts\python.exe -c "from huggingface_hub import snapshot_download as d; d('stabilityai/sd-turbo', local_dir='models/sd-turbo', ignore_patterns=['sd_turbo.safetensors','*.fp16.safetensors','*.png','*.jpg'])"
```

The ignore patterns skip duplicate single-file and fp16 copies the app does not use.

**B1.2** Check that `models\sd-turbo` exists and contains `model_index.json`, `unet`, `vae` and `text_encoder`:

```powershell
dir models\sd-turbo
```

### B2. Add the model to the app's model list

**B2.1** Open `configs\lcm-models.txt` and add this line at the end of the file, on its own line:

```
models/sd-turbo
```

### B3. Verify it works offline

**B3.1** Disconnect the machine: turn Wi-Fi off, unplug the network cable, or enable airplane mode.

**B3.2** Double-click `start-webui-offline.bat` and open <http://127.0.0.1:7860>.

**B3.3** Under **Mode**, select **LCM**. Open **Models** and set **LCM model** to `models/sd-turbo`.

**B3.4** Open **Generation Settings** and set Inference Steps to 4, Image Height and Width to 512, and Guidance Scale to 1. Check that **Use locally cached model or downloaded model folder(offline)** is ticked.

**B3.5** Open **Text to Image**, type any prompt and click **Generate**.

**B3.6** Open **Image to Image**, upload any picture, set **Strength** to 0.8 and click **Generate**.

**B3.7** Success means both images appear (about 25 s each on a laptop CPU) and the terminal shows no download messages or connection errors. If the model fails to load, reconnect, rerun the B1.1 command, and repeat B3.

Path 1 is ready. See [USAGE.md](USAGE.md) for how to use it.

## Part C: Path 2 setup (SDXL-Turbo)

Requires Part A. Does not require Part B.

### C1. Apply the SDXL-Turbo fix (online)

On a fresh install, SDXL-Turbo on CPU can fail with "mat1 and mat2 must have the same dtype, but got Half and Float". Apply this fix before the first run. (The same change is in [../../fastsdcpu_local/fastsdcpu-local.patch](../../../fastsdcpu_local/fastsdcpu-local.patch).)

**C1.1** Open `src\backend\lcm_text_to_image.py` in the `fastsdcpu` folder and find this block (about line 515):

```python
if not self.use_openvino and not is_openvino_device():
    self._pipeline_to_device()
```

**C1.2** Add the `elif` straight after it, at the same indentation:

```python
if not self.use_openvino and not is_openvino_device():
    self._pipeline_to_device()
elif not self.use_openvino:
    # transformers>=5 keeps the stored (fp16) dtype for text encoders,
    # so cast every component explicitly to avoid Half/Float mismatches
    for component in self.pipeline.components.values():
        if isinstance(component, torch.nn.Module):
            component.to(dtype=self.torch_data_type)
```

A `git pull` overwrites this edit, so reapply it after updating.

### C2. Download the model (online, about 13 GB)

Offline mode needs complete model files in a folder. The app's own automatic download is not enough: its cache holds only the files the app used, and offline mode then fails with `IncompleteSnapshotError`. A local model folder avoids that.

**C2.1** In PowerShell, in the `fastsdcpu` folder:

```powershell
env\Scripts\python.exe -c "from huggingface_hub import snapshot_download as d; d('stabilityai/sdxl-turbo', local_dir='models/sdxl-turbo', ignore_patterns=['sd_xl_turbo_1.0*.safetensors','*.fp16.safetensors','*.onnx','*.onnx_data','vae_decoder/*','vae_encoder/*','*.png','*.jpg'])"
```

The ignore patterns skip duplicate single-file, fp16 and ONNX copies the app does not use. Without them the repository alone is 55 GB.

**C2.2** Check that `models\sdxl-turbo` exists and contains `model_index.json`, `unet`, `vae`, `text_encoder` and `text_encoder_2`:

```powershell
dir models\sdxl-turbo
```

### C3. Add the model to the app's model list

**C3.1** Open `configs\lcm-models.txt` and add this line at the end of the file, on its own line:

```
models/sdxl-turbo
```

### C4. Verify it works offline

**C4.1** Disconnect the machine: turn Wi-Fi off, unplug the network cable, or enable airplane mode.

**C4.2** Close other large programs (about 11 GB of RAM is needed). Double-click `start-webui-offline.bat` and open <http://127.0.0.1:7860>.

**C4.3** Under **Mode**, select **LCM**. Open **Models** and set **LCM model** to `models/sdxl-turbo`.

**C4.4** Open **Generation Settings** and set Inference Steps to 4, Image Height and Width to 512, and Guidance Scale to 1. Check that **Use locally cached model or downloaded model folder(offline)** is ticked.

**C4.5** Open **Text to Image**, type any prompt and click **Generate**. The first run is slower because the model has to load into RAM.

**C4.6** Open **Image to Image**, upload any picture, set **Strength** to 0.8 and click **Generate**.

**C4.7** Success means both images appear (about 70 s each on a laptop CPU) and the terminal shows no download messages or connection errors. If the model fails to load, reconnect, rerun the C2.1 command, and repeat C4.

Path 2 is ready. See [USAGE.md](USAGE.md) for how to use it.

