# Sketch to image with local models (FastSD CPU), phase 1 of the project

Question: can a hand-drawn sketch plus a short text give a usable picture on a CPU laptop in seconds? Tested 2026-11-05 to 07 with FastSD CPU (a web UI with an API) on a Core 7 150U laptop, 512 x 512, one sketch, one scene text ("one skeleton dancing next to a large campfire with a stone ring, campfire in the center, skeleton on the right side, night forest of tall pine trees, full moon and stars"), four style prefixes (pixel art, impressionist, hyperrealistic, none) and three seeds. The setup is in [../docs/local-models/fastsd-cpu/](../docs/local-models/fastsd-cpu/INSTALL.md); the patch and offline start script are in `../fastsdcpu_local/`. The app no longer runs any model locally ([../docs/local-models/README.md](../docs/local-models/README.md)); this is kept as a record of what local sketch-to-image looks like.

## Three paths

| Path | Model | How the sketch is used |
|---|---|---|
| P1 | SD-Turbo, image to image | the sketch is the start image, Strength 0.7 / 0.8 |
| P2 | **SDXL-Turbo, image to image** | the same; the recommended path |
| P3 | SD 1.5 + LCM-LoRA + scribble / Canny ControlNet | the sketch is a control image, conditioning scale 0.7 |

## Findings (120-image confirmation test, 3 seeds)

- **SDXL-Turbo image to image with a filled-in sketch is the best path.** Strength 0.8 and 0.9 at 4 steps give pixel-identical images (both run 3 real steps), so they are one setting. It kept the layout in 12 of 12 images (one skeleton on the right, a central campfire, moon, night forest); Strength 0.7 kept the layout in 12 of 12 too but restyles less.
- **A raw (unfilled) sketch gives a pale daytime picture** with the moon as a circle or arc; a filled sketch gives night with a moon. Fill the sketch.
- **SD-Turbo (P1) is worse than SDXL-Turbo at the same strength:** the skeleton is usually present but less clear, and at 0.7 the campfire turned into a red blob in 8 of 12 images.
- **ControlNet (P3) follows the layout best** (12 of 12) but needs a second model and gave few pictures the author wanted (2 of 12 kept); text only (SD 1.5 + LCM-LoRA) mostly lost the skeleton (3 of 12).
- **Text-only SDXL-Turbo** has the highest keep rate (6 of 12) but does not follow the layout: skeleton and moon positions vary.
- **Style prefixes:** with a filled sketch hyperreal and "none" look almost the same and impressionist is modest; text-only SDXL-Turbo shows clearly different styles. Hyperreal was never kept (0 of 30).
- **Seed matters:** seed 42 gave 14 of the 27 kept images. Three seeds and one sketch are too few for fine differences.
- **Speed:** about 58-70 s per 512 px SDXL-Turbo image (4 steps) on this CPU; on a Kaggle T4 about 1.5 s ([../docs/models/sdxl-turbo.md](../docs/models/sdxl-turbo.md)).

## Files

| File / folder | What |
|---|---|
| `final/` | one contact sheet per path with the chosen setting (3 seeds): `FINAL_path1_sdturbo_img2img.png`, `FINAL_path2_sdxlturbo_img2img.png` (recommended; seed 2024 duplicates the skeleton), `FINAL_path3_controlnet_neutral.png` (best layout adherence, 2 seeds) |
| `inputs/` | the sketches and control images used (`sketch_original`, `sketch_filled`, `init_*`, `control_*`) |
| `run_tests.py` | shared settings, prompts and styles; drives the FastSD CPU web UI API |
| `run_confirm.py`, `run_confirm_text.py` | the confirmation test: `python run_confirm.py <A\|B\|C\|D>` (blocks A and B share one SDXL pipeline run, so run `A`), and the text-only blocks |

File names of generated pictures: `<block>__<path>__<input>__<settings>__seed<seed>__<style>.png` (`strNN` = image-to-image Strength, `scaleNN` = ControlNet scale, `stepsN`, `gX` = guidance). The individual pictures, the per-path sheets, the ranking spreadsheet and the pre-registered test plan were removed on 2026-11-11 (reference repository `layer-prototype`).
