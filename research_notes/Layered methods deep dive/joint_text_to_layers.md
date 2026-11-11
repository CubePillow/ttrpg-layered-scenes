# Joint text-to-multi-layer methods: release status and paper facts (checked 2026-11-09)

The one methods note: which layered-generation papers have code and weights, what they take as input, and whether they fit a T4. Our use: [papers-survey.md](../../docs/research/papers-survey.md), [ideas considered](../../docs/ideas-considered/README.md). **[U]** = not verified this pass.

**Takeaway.** PSDiffusion, DreamLayer, OmniPSD, LayerFusion, LASAGNA and ART all generate layers jointly from a global prompt plus per-layer prompts or boxes, but none has verified, downloadable, usable weights except ART+ (Flux-class, hard on a T4). The runnable native text-to-RGBA options are single-layer (or fg + bg): LayerDiffuse, LayerDiffuse-Flux and Qwen-Image-2.1. The architecture "global branch plus per-layer branches with shared attention" is well established (PSDiffusion and DreamLayer on SD, OmniPSD on FLUX); PSDiffusion is closest to an SDXL + LayerDiffuse stack but cannot be run.

## Release status and fit

| Method | Base | Release (checked 2026-11-09) | Licence | Fit for us |
|---|---|---|---|---|
| **PSDiffusion** (2505.11468, WACV 2026) | SDXL + rank-256 LoRA + RGBA VAE; about 60 A800 GPU-hours to train | not released (README TODOs open, last push 2025-05-15) | n/a | would fit a T4; training not feasible on Kaggle quotas; layer-wise editing claimed without procedure |
| **DreamLayer** (2503.12838, ICCV 2025) | SD1.5, K/V-only fine-tune | **dataset only** ([HF LL3RD/DreamLayer](https://huggingface.co/datasets/LL3RD/DreamLayer), about 400k samples, Apache-2.0); code "coming soon" | dataset Apache-2.0 | the most realistic "train our own joint model" (a K/V or LoRA fine-tune on SDXL plausible on one T4 [U]); latent move / flip / resize with shadows |
| **OmniPSD** (2512.09247) | FLUX.1-dev 2×2 grid (composite, fg, mid, bg) + RGBA VAE; Kontext for image-to-PSD | code + dataset subset, **no weights** (placeholder `LORA_PATH`, no "FLUX.1-dev-alpha" VAE link) | code CC BY-NC-SA 4.0, dataset Apache-2.0 | can't run; Flux LoRA training on a T4 impractical |
| **LASAGNA** (2601.15507, UCSC + Adobe) | about 2B Adobe-internal DiT, RGBA VAE, T5 | not released (dataset LASAGNA-48K "will be released") | n/a | concept only: FG_Gen / BG_Gen = "regenerate one layer given the rest" ≈ released LayerDiffuse SD1.5 fg-given-bg |
| **LayerFusion** (2412.04460, Virginia Tech + Adobe) | SDXL (RealVisXL v4) + LayerDiffuse fg weights; **training-free** | no code | n/a | **directly reimplementable on our LayerDiffuse SDXL**: fg / bg / blend branches in parallel; at t = 0.8T take a structure prior (fg last self-attention) and a content prior (cross-attention at EOS) as soft / hard masks, blend attention outputs, share attention between blend and bg. Extending 1 → N fg branches is our own extension |
| **ART** (2502.18364, MSRA) | FLUX.1-dev, 3D RoPE, region-wise attention (12× faster than full attention, "50+ layers") | **withdrawn 2025-07-23** (training data "may have come from illegal sources") | MIT repo, weights removed | do not use |
| **ART+ / PrismLayers** (2505.22523) | ART fine-tuned on PrismLayersPro | code ([redredsheep/PrismLayers](https://github.com/redredsheep/PrismLayers)) + Google Drive checkpoints; unofficial HF mirror `24yearsold/PrismLayers_ckpt` (5.56 GB); the base ART checkpoint may be the withdrawn weights [U] | MIT repo, Apache-2.0 dataset | the only downloadable joint text-to-multi-layer model (global caption + boxes, variable layers); Flux-class, hard on a T4; tried: [art-plus.md](../../docs/ideas-considered/models/art-plus.md) |
| **CLD** (2511.16249) | FLUX.1-dev + inpainting ControlNet + LoRAs | code (MIT) + weights (Apache-2.0, Flux-dev NC applies) | | image → layers by boxes, not joint text-to-layers; in the prototype ([cld.md](../../docs/models/cld.md)) |
| **LayerDiffuse-Flux** (RedAIGC) | FLUX.1-dev | weights on HF (AFL-3.0 + Flux NC) | | single RGBA layer only |
| **Qwen-Image-2.1** | 7B DiT, Qwen3-VL | diffusers pipeline, BF16 weights | Qwen Research (non-commercial) | text → RGBA via a prompt phrase, edit transparent layers, extract subjects, up to 10 references; **no multi-layer stack** |
| LayerCraft | FLUX LoRA (Object Integration Network) | code + OIN LoRA on Google Drive | no licence reported | not tried |
| LayerDecomp (Adobe), DiffDecompose, Text2Layer, LayeringDiff, RefLayer (2602.19358), LiWi, PixelART | | not released / not found | | LayerDecomp keeps shadows and reflections in the transparent layer |
| See-through (anime, SIGGRAPH 2026) | LayerDiff 3D + Marigold, NF4 variant | code + HF `layerdifforg/*` | Apache-2.0 code, RAIL++-M weights [U] | anime only |
| LayerD (2509.25134, ICCV 2025) | BiRefNet matting + inpainting, CPU | code (archived) + `cyberagent/layerd-birefnet` | Apache-2.0 | tried, see [layerd.md](../../docs/ideas-considered/models/layerd.md) |

## Paper facts

- **PSDiffusion:** input = a global prompt plus N layer prompts (an LLM can write them), no boxes; layout comes from the global branch's cross-attention ("layer cross-attention reweighting"), and "partial joint self-attention" lets each layer attend to its masked region of the global branch; dataset 3-6 layers, evaluated with 3 fg + 1 bg.
- **DreamLayer:** one prompt for the background and one per foreground merged into a global prompt that drives a "global layer"; Context-Aware Cross-Attention (layout), Layer-Shared Self-Attention (links all layers), Information-Retained Harmonization (latent blending that produces shadows); 2-4 layers; boxes (GroundingDINO) only to build the dataset.
- **OmniPSD:** text-to-PSD takes a poster description plus fg / mid / bg descriptions (removing the per-layer prompts worsened FID 30.43 → 38.56); coherence from in-context spatial self-attention; poster editing in a UI, no single-layer re-prompt.
- **LASAGNA:** modes Text2All (composite + clean background + RGBA foreground with shadows and reflections), FG_Gen, BG_Gen.
- **ART / PrismLayers:** PrismLayers is about 200K multi-layer images (average about 7 layers, range 3-14; a 20K "Pro" subset) built with LayerFLUX (single transparent layer) and MultiLayerFLUX (composes layers from a layout given by a reference image or an LLM); ART+ wins about 60 % of user-study comparisons. Run: `python multi_layer_gen/demo.py -c multi_layer_gen/demo.yaml -i inference_layout/test_1.json`; JSON = `whole_image.caption` ("This is a [STYLE] style image. …") + `layout` boxes.
- **LayeringDiff** generates a composite then extracts layers; **TransPixar** (Adobe + HKUST, 2501.03006) is RGBA text-to-video with alpha tokens (CogVideoX-5B LoRA released).
- Joint methods give the best cross-layer lighting harmony, but regenerating one layer means re-running everything or inpainting-style tricks with a fixed seed. No VRAM figures are published for any joint model.

## Candidates ranked at the time

1. LayerFusion-style training-free harmonisation on LayerDiffuse SDXL (no weights, hardware we have; single-layer regeneration = rerun one fg branch against the frozen blend / bg).
2. ART+ released weights (run on an A100-class GPU or a quantised build on a T4; check provenance and Drive sizes first).
3. DreamLayer dataset plus a small K/V / LoRA fine-tune.

(The prototype then took a different path, generate one picture and split it: [pipeline.md](../../docs/concepts/pipeline.md).)
