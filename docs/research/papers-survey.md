# Layered-generation methods: one table

> **Role: current overview (high).** Every layered-generation / decomposition method we found, one row each, with release status and what it does on our hardware. Measured numbers: [../models/README.md](../models/README.md); per-model detail: the factsheets in [../models/](../models/README.md). Release status re-checked 2026-11-09. [U] = unverified.

## 1. Methods we can run

| Method (paper) | Input → output | Base | Code · weights · licence | On our 2× T4 (measured) | Editing ops | Factsheet |
|---|---|---|---|---|---|---|
| **Qwen-Image-Layered** (2512.15603) | image → N RGBA layers (hidden areas filled) | 20B MMDiT | ✅ · ✅ · Apache-2.0 | ✅ 27–35 s (384 px, 4 layers, 4 steps) | recursive re-split; edit a layer with any editor | [qwen-image-layered](../models/qwen-image-layered.md) |
| **Stable-Layers** (Stability AI) | image → N layers (RL-tuned LoRA on the above) | Qwen-Image-Layered | ✅ · ✅ · Stability Community | ✅ 102 s at 640 px (one clean layer per object, also on the night and rain edits); colour shift | as above | [stable-layers](../models/stable-layers.md) |
| **RevealLayer** (ICML 2026) | image + box per object → layers incl. hidden parts + filled background | FLUX.1-dev + LoRA + refiner | ✅ · ✅ · Apache-2.0 (+ FLUX-dev NC) | ✅ 134 s (512 px, 12 steps) | controllable grouping by boxes; amodal completion | [revealayer](../models/revealayer.md) |
| **ART+ / PrismLayers** (2505.22523) | caption + boxes → layers (joint, no input image) | FLUX.1-dev + ART LoRAs | ✅ · ✅ (Drive; ART base also in `thuteam/CLD`) · MIT | ⚠️ full-size coherent scenes (≈ 5 min, 8.2 GB); layers still opaque (decoder being fixed) | variable layer count, 21 styles | [art-plus](../ideas-considered/models/art-plus.md) |
| **CLD** (2511.16249) | image + caption + box per layer → layers | FLUX.1-dev + ControlNet adapter + LoRAs | ✅ · ✅ · MIT / Apache-2.0 (+ FLUX-dev NC) | ✅ 116-459 s at 512 px, slow but decent layers; invents its background | decomposition by boxes | [cld](../models/cld.md) |
| **LayerDiffuse** (2402.17113) | text → transparent object; object into a given background and back out | SDXL / SD1.5 | ✅ · ✅ · Apache-2.0 / OpenRAIL-M | ✅ 18 s per element (1024 px) | our chain: add / re-prompt a layer in context; `relocate()` | [layerdiffuse-sdxl](../ideas-considered/models/layerdiffuse-sdxl.md) |
| **LayerDiffuse-Flux** | text → transparent object | FLUX.1-dev + LoRA + transparent VAE | ✅ · ✅ · AFL-3.0 (+ FLUX-dev NC) | ✅ 58 s, semi-transparent glass works | single layer only | [layerdiffuse-flux](../ideas-considered/models/layerdiffuse-flux.md) |
| **Qwen-Image-2.1** | text → RGBA; edit an RGBA layer; extract a subject | 7B DiT, Qwen3-VL, 4-channel VAE | ✅ · ✅ · Qwen Research (NC) | ✅ 17–23 s per call | layer re-prompt keeping alpha, extraction, ≤ 10 references; no multi-layer split | [qwen-image-2.1](../models/qwen-image-2.1.md) |
| **LayerD** (ICCV 2025) | image → layers by peeling (matte top layer, inpaint, repeat) | BiRefNet + LaMa | ✅ · ✅ · Apache-2.0 (archived) | ⚠️ CPU 60 s; returned 1 layer on painted scenes | — | [layerd](../ideas-considered/models/layerd.md) |
| **SAM2 + LaMa** (+ pix2gestalt) | image → cut-out layers + inpainted background | SAM2, LaMa | ✅ · ✅ · Apache-2.0 | ✅ 7 s by noun (Grounding DINO + SAM2): clean object layers; blurry LaMa fill | segment by noun, object cut-outs | [sam2-lama](../models/sam2-lama.md) |
| Qwen-Image-Lightning LoRA | speed LoRA tried on Qwen-Image-Layered | Qwen-Image | ✅ · ✅ · Apache-2.0 | ⚠️ no speed-up at 4 steps; separates thin subjects | — | [qwen-lightning](../models/qwen-lightning.md) |

## 2. Methods we cannot run (no weights or code)

| Method (paper) | Input → output | Base | Release status | What we borrow |
|---|---|---|---|---|
| **LayerFusion** (2412.04460) | joint fg + bg + blend, harmonised | SDXL (RealVisXL) + LayerDiffuse fg | no code, but **training-free** | attention blending: masks from the fg branch's self-attention and `<EOS>` cross-attention at t = 0.8T; `a'_Blended = a_FG·m_soft + a_Blended·(1 − m_soft)`, `a'_FG = a'_Blended·m_hard + a_FG·(1 − m_hard)`. No move/resize in the paper. Re-implementable on our stack. |
| **DreamLayer** (2503.12838) | joint 2–4 layers with move / flip / resize and following shadows | SD1.5, K/V fine-tune | code "coming soon"; **dataset released** (`LL3RD/DreamLayer`, ~400k samples) | its harmonisation step → our `relocate()`; a K/V fine-tune on its dataset is feasible [U] |
| **PSDiffusion** (2505.11468) | joint multi-layer generation | SDXL + rank-256 LoRA + RGBA VAE | "code coming soon" | partial joint self-attention (training-free approximation); retraining ≈ 60 A800-h |
| **OmniPSD** (2512.09247) | text / image → PSD (fixed fg/mid/bg grid) | FLUX.1-dev + Kontext + RGBA VAE | code ✅, **weights ❌** | — (Flux training on a T4 impractical) |
| **LASAGNA** (2601.15507) | text → composite + background + foreground with shadows and reflections | ~2B Adobe DiT | not released | effects-with-layers idea; its fg-given-bg mode ≈ LayerDiffuse SD1.5 |
| **ART** (2502.18364, Microsoft) | caption + layout → layers | FLUX.1-dev | **withdrawn 2025-07** (data provenance) | superseded by ART+ |
| LayeringDiff, LayerDecomp, DiffDecompose, Text2Layer, RefLayer, LiWi, PixelART | various decomposition / layered generation | — | not released (re-checked) | — |
| LayerCraft | LLM agents plan and edit layered images | — | code + LoRA (object insertion, not a layer generator) | design reference for our planner and event router |
| Alfie · See-through · Generative Omnimatte · TransPixar | sprites · anime PSD (23 layers) · video layers · RGBA video | — | code ✅ | not tried (sprites / anime only / video) |

## 3. Move and resize in the papers

| Approach | Who | How identity and lighting are handled |
|---|---|---|
| Latent move with joint re-denoising | **DreamLayer** (only paper with move/resize) | denoise each layer alone to t ≈ 600/1000, apply the edit to the fg latents and alpha, composite, denoise together → shadows follow. Training-free in itself; basis of our `relocate()` ([../concepts/editing.md](../concepts/editing.md)). |
| Re-composite only | Qwen-Image-Layered, Stable-Layers, CLD, RevealLayer | pixel move; lighting and shadows stay stale |
| Attention blending, no spatial edit | LayerFusion | harmonised joint generation only |
| Latent pinning + self-attention K/V sharing | DragonDiffusion, DiffEditor, RegionDrag, InstantDrag, DesignEdit, GeoDiffuser, Magic Fixup, DiffUHaul | keeps identity while moving inside a flat image |

## Sources
Release and method notes (cited findings): [joint_text_to_layers.md](../../research_notes/Layered%20methods%20deep%20dive/joint_text_to_layers.md) , [other_psd_methods.md](../../research_notes/Layered%20methods%20deep%20dive/other_psd_methods.md), [spatial_edit_mechanics.md](../../research_notes/Layered%20methods%20deep%20dive/spatial_edit_mechanics.md). The index of all notes: [../../research_notes/README.md](../../research_notes/README.md).
