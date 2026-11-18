# Glossary

> **Role: reference (stable).** Terms used across the docs.

| Term | Meaning |
|---|---|
| **Layer** | A full-canvas RGBA image (colour + alpha/transparency) holding one object or the background. Layers stack back to front. |
| **Split / decomposition** | Turning one finished image into several layers (Qwen-Image-Layered, RevealLayer, LayerD, SAM2 + LaMa). |
| **Recomposite** | Alpha-compositing all layers back into one image. |
| **Recomposite diff** | Mean absolute pixel difference (0–255) between the input image and the recomposite. Low = the layers still reproduce the input; it does not measure how well objects are separated. |
| **Amodal completion** | Filling in the parts of an object (or of the background) that were hidden behind something else. |
| **Steps** | Number of denoising iterations. Fewer = faster, usually softer. |
| **CFG / `true_cfg`** | Classifier-free guidance: runs the model twice per step (with and without the prompt). CFG 1 = one pass, about 2× faster. |
| **Strength (s)** | In image-to-image: how much of the denoising schedule is redone (0.3 = the last 30%). Low keeps the input, high redraws more. |
| **Scheduler / sampler** | The update rule between steps. Euler: one model call per step, deterministic. Heun: two calls per step, more accurate. DPM++ SDE: stochastic (adds fresh noise each step). |
| **LoRA** | A small add-on weight file that adapts a base model (e.g. LayerDiffuse's transparency LoRA, Stable-Layers, Lightning). "Unmerged" = applied on the fly next to the base weights instead of baked in. |
| **GGUF, Q4_K_S** | A compressed (quantised) weight format; Q4_K_S ≈ 4 bits per weight. Lets the 20B Qwen-Image-Layered (40 GB in bf16) fit on two 16 GB T4s. |
| **bf16 / fp16 / fp32** | Number formats. Many new models are trained in bf16; the T4 has no fast bf16, and fp16 overflows above 65504. |
| **`fp16_mixed`** | Our patch ([concepts/fp16-on-t4.md](concepts/fp16-on-t4.md)): fast fp16 matrix multiplies with scaled inputs, everything else in fp32, so bf16 models run on a T4 without NaNs. |
| **NaN / overflow** | "Not a number": what fp16 produces once values exceed its range; one NaN spreads and turns the image into noise or black. |
| **LayerDiffuse modes** | `fg` (transparent object alone), `bg2ble` (draw an object into a given background), `bgble2fg` (extract that object as a transparent layer), `fg2ble`/`fgble2bg` (the reverse). See [LayerDiffuse modes](ideas-considered/models/layerdiffuse-sdxl.md#modes-how-layerdiffuse-works). |
| **Chain** | Our LayerDiffuse scene-to-layer chain: `bg2ble → bgble2fg` per new element, on the current composite. |
| **`relocate()`** | Our move/resize with re-harmonisation ([editing.md §1](concepts/editing.md#1-move--resize-with-re-harmonisation-relocate)). |
| **Pinning** | During re-harmonisation, replacing the latents inside an object with its original (re-noised) latents so only its rim and surroundings change. |
| **Paste-back** | After decoding, blending the original object pixels back inside its alpha, to keep identity exactly. |
| **Identity drift** | A moved or edited object coming out redrawn (changed shape, colour, details). |
| **Re-harmonisation** | Making a moved/added object fit its new spot: lighting, glow, contact, shadow. |
| **Story event** | A narrative change that affects the scene ("it starts to rain", "the campfire goes out"); routed to per-layer actions ([editing.md §3](concepts/editing.md#3-story-events-across-layers)). |
| **Drift (over turns)** | How much unedited parts of a scene change over many successive edits ([research/drift-evaluation.md](research/drift-evaluation.md)). |
| **Kaggle batch run** | A notebook pushed with the CLI that runs unattended (max 2 GPU runs at once). |
| **Happy path** | The settings and steps that give a model's best result with the least effort, as recorded in its factsheet. |
