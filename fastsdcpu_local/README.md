# Local changes to FastSD CPU

[FastSD CPU](https://github.com/rupeshs/fastsdcpu) is not stored here. The sketch-to-image tests used it at commit `85b2d79b3c075e6b0f2d1d9ee0cf4a1638b5fed8` with these local changes:

- `fastsdcpu-local.patch`:
  - `src/backend/lcm_text_to_image.py` casts the pipeline components to float32 on CPU. This fixes SDXL-Turbo's "Half and Float" error with transformers 5.
  - `configs/lcm-models.txt` lists the local model folders `models/sdxl-turbo` and `models/sd-turbo`. These folders must be downloaded first ([INSTALL.md](../docs/local-models/fastsd-cpu/INSTALL.md) B1 and C2).
  - `configs/stable-diffusion-models.txt` adds `stable-diffusion-v1-5/stable-diffusion-v1-5`. Only the dropped Path 3 used it.
- `start-webui-offline.bat`: starts the web UI with all network access blocked (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, no Gradio analytics), using the local model folders.
- Not in the patch: `configs/settings.yaml` is ignored by FastSD CPU's git. Set `use_offline_model: true` in it by hand ([INSTALL.md](../docs/local-models/fastsd-cpu/INSTALL.md) A3.1).

Apply them:

1. Clone FastSD CPU next to this folder at the tested commit:
   ```bash
   git clone https://github.com/rupeshs/fastsdcpu.git && cd fastsdcpu && git checkout 85b2d79b3c075e6b0f2d1d9ee0cf4a1638b5fed8
   ```
2. Apply the patch and copy the starter script:
   ```bash
   git apply ../fastsdcpu_local/fastsdcpu-local.patch && cp ../fastsdcpu_local/start-webui-offline.bat .
   ```
3. Follow [../docs/local-models/fastsd-cpu/INSTALL.md](../docs/local-models/fastsd-cpu/INSTALL.md) for the environment, the model downloads and offline mode. Then follow [../docs/local-models/fastsd-cpu/USAGE.md](../docs/local-models/fastsd-cpu/USAGE.md) to generate images. Note that `git pull` would overwrite the patch.

The guides do the same changes by hand, so you can use either the guides or this patch.
