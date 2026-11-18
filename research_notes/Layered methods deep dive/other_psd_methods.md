# Other text/image-to-PSD and layer-decomposition methods (audit, 2026-11-09)

Methods beyond those in [joint_text_to_layers.md](joint_text_to_layers.md). [U] = not confirmed on GitHub / HF in this pass. T4 = 16 GB, fp16 only. Later measurements: Stable-Layers and RevealLayer in [docs/models](../../docs/models/README.md); LayerD and SAM2 + LaMa tried ([layerd.md](../../docs/ideas-considered/models/layerd.md), [sam2-lama.md](../../docs/models/sam2-lama.md)).

| Method | Type | Code / weights | Licence | T4 fp16 | Why it matters |
|---|---|---|---|---|---|
| Generate → SAM2 → amodal inpaint (pix2gestalt / LaMa) | pipeline | yes | mixed | yes | cheapest fully runnable image-to-PSD route; the route we built |
| LayerD (ICCV25, CyberAgent, [2509.25134](https://arxiv.org/abs/2509.25134)) | graphic design → layers by repeatedly matting the top layer (`cyberagent/layerd-birefnet`, about 1 GB) and inpainting (simple-lama) | yes | Apache-2.0 | yes | iterative peel-and-inpaint template; trained on Crello posters, so natural scenes are out of domain |
| RevealLayer (ICML26, [2605.11818](https://arxiv.org/abs/2605.11818)) | image + boxes → RGBA layers incl. hidden content | yes; RevealLayer-100K and RevealLayerBench (200 images) | Apache-2.0 | measured, 2× T4 | "move object, background stays complete" |
| Stable-Layers (Stability AI, [2605.30257](https://arxiv.org/abs/2605.30257)) | LoRA over Qwen-Image-Layered, RL-tuned with VLM scores | inference repo | community licence | measured, GGUF stack | better than the base model |
| See-through (shitagaki-lab) | anime image → up to 23 PSD layers with depth order (Live2D oriented) + ComfyUI node | yes | [U] | [U] | strong only for anime / 2D art |
| LayerCraft ([2504.00010](https://arxiv.org/abs/2504.00010)) | LLM agents plan layout (CoT), generate the background, integrate objects layer by layer | GitHub + OIN LoRA | [U] | [U] | orchestration reference |
| Alfie (ECCV24-W, [2408.14826](https://arxiv.org/abs/2408.14826)) | training-free RGBA text-to-image from DiT attention maps | GitHub | [U] | likely | single objects, not scenes |
| Referring Layer Decomposition / RefLayer ([2602.19358](https://arxiv.org/abs/2602.19358)) | image + text → named RGBA layer; RefLade 1.11M dataset | none found | | | text-targeted extraction |
| Generative Omnimatte (CVPR25, [2411.16683](https://arxiv.org/abs/2411.16683)) | video → object + effect layers (VideoX-Fun, SAM2) | public reimplementation | [U] | doubtful | only if scenes get animated |
| TransPixar (CVPR25) | text → RGBA video, CogVideoX-5B LoRA | yes | HF card Apache-2.0 | no (about 24 GB) | animated transparent effects |
| LayeringDiff ([2501.11197](https://arxiv.org/abs/2501.11197)) | generate a composite, then disassemble | not found | | | same philosophy as route 1 |
| LayerDecomp (Adobe, CVPR25, [2411.17864](https://arxiv.org/abs/2411.17864)) | image → fg / bg including shadows and reflections (5B DiT) | no code | | | idea: keep shadows with the object layer |
| DiffDecompose ([2505.21541](https://arxiv.org/abs/2505.21541)), Text2Layer (2023), MuLAn ([2404.02790](https://arxiv.org/abs/2404.02790), 44K multi-layer annotations) | various | placeholder / mismatched / dataset | | | not usable / historical / training data |
| UniWorld-Design (2608.03971), LiWi (2605.14552), Inpainting → Layer Decomposition (2511.20996) | 2026 decomposition papers citing Qwen-Image-Layered | none found | | | watch list |

Not found / not audited: PixelART, TransAnimate, SemLayer (2603.24039, icons), AmodalSVG (2604.10940). Curated list for sweeps: [awesome-image-layer-decomposition](https://github.com/discopotato3376-oss/awesome-image-layer-decomposition).

**Generate → segment → amodal complete** (the baseline): generate the scene (SDXL), segment with SAM2 (Apache-2.0, boxes from a detector or LLM plan), complete hidden parts with pix2gestalt (CVPR24, SD-based, weights on HF, [repo](https://github.com/cvlab-columbia/pix2gestalt), licence [U]) or Open-World Amodal Appearance Completion (CVPR25, [U]), inpaint the background hole with LaMa / SD inpaint, export RGBA layers with z-order to PSD (psd-tools / pytoshop). Move and resize are free; re-prompting a layer means regenerating or inpainting it, then harmonising.
