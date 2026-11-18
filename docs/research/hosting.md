# Hosting, compute, costs and base models

> **Role: research synthesis.** Where things run, the free and cheap options, the TPU route, the helper models we looked at and the licences that matter. Costs of paid APIs, university GPU access and the hosted text-to-image models are parked in [../ideas-considered/hosting-options.md](../ideas-considered/hosting-options.md). [U] = unverified, [est] = estimate.

## 1. What we use now
- **Kaggle (free):** 2× T4 16 GB (or 1× P100), about 30 GPU-h/week, sessions up to 12 h, about 29 GB RAM, internet after phone verification. **Max 2 batch GPU sessions at once.** No native bf16/fp8 on T4 → [../concepts/fp16-on-t4.md](../concepts/fp16-on-t4.md). Terms: personal, non-commercial use; no serving farms. Workflow: [../guides/kaggle.md](../guides/kaggle.md).
- **Laptop CPU (Core 7 150U):** only the thin app now; the earlier CPU runs (Ollama, SDXL-Turbo at about 60–160 s per image, CPU-tested modules) were measurements, no model runs there any more. Speed-ups: [cpu-speedups.md](../local-models/cpu-speedups.md).

## 2. Free and cheap options (from the 11-05 research)
| Option | Cost | GPU | Catch |
|---|---|---|---|
| Kaggle notebooks | free | 2× T4 / P100 | weekly quota, 2 batch sessions |
| LMU CIP pool (Slurm) | free | RTX 2060 SUPER 8 GB | jobs pause when someone uses the machine |
| LMU abakus servers | free | stronger cards (A5000 24 GB per earlier research) | request by mail to the RBG with a good reason (thesis, publication, project) |
| LRZ AI Systems | free for research | P100 / V100 / A100 / H100 | needs an AI-enabled LRZ project via a chair |
| Google Colab free | free | usually T4 | web UIs / serving forbidden; code cells only |
| HF Spaces ZeroGPU | free | shared | about 5 GPU-min/day |
| Modal | $30/month credit | T4/L4/A10 | clean live HTTPS endpoint |
| Pay-per-image hosts (fal, WaveSpeed, Replicate, Together, Runware) | about $0.001–0.015 per image for small models | managed | card + prepaid credit |
| Comfy Cloud | from $20/month | RTX PRO 6000 (96 GB) | proprietary paid UI (the team prefers to avoid it); runs Qwen-Image-Layered in seconds |
| SageMaker Studio Lab, Lightning AI | closed to new users / one-time trial | - | not recurring |

<a id="tpu"></a>
## 3. TPU
- Kaggle offers TPU v5e-8 (8 chips × 16 GB HBM, native bf16) on a separate 20 h/week quota. Template: diffusers' PyTorch/XLA FLUX SPMD example (tested on v5e-8). Estimated about 40 s per Qwen split at about 30 steps; the "2–5 days" effort figure was an unverified guess.
- **Probe (2026-11-09):** three CLI batch runs never got a TPU (Kaggle stored `machine_shape: TpuV5E8`, the run used the standard CPU image). The image ships torch 2.11 (CPU) + JAX 0.11.1 and no torch_xla; pip's newest torch_xla is 2.9, so torch must be pinned to 2.9. **2026-11-10 interactive attempt:** the editor offers "TPU v5e-8" (TPU quota shown as 00:00 / 20 hrs) but the session sat in a queue: "TPUs are popular right now. You are #1510 in the queue". No TPU was allocated, so no probe stage ran. **Next:** retry at a quieter time (the queue position is shown in the editor), or skip the TPU route.

### TPU software routes (researched, not measured)

| Route | Status | Notes |
|---|---|---|
| PyTorch/XLA + diffusers SPMD | template exists (diffusers PR #13474, FLUX on v5e-8, ~1.76 s steady state [U]) | shard params with `xs.mark_sharding`; text encoders on CPU; ~195 s first compile; recompile issues reported |
| TorchTPU (Google, open-sourced 2026-10-20 [U]) | `pipe.to("tpu")`; 96.5% of diffusers tests pass [U] | not confirmed on Kaggle; Qwen-Image and multi-chip sharding unknown |
| JAX / MaxDiffusion | SD, SDXL, Flux, Wan on v5e/v6e | no Qwen-Image port; a JAX port would be a large effort |

**Blockers:** memory fits (40 GB / 8 chips ≈ 5 GB per chip on v5e); several minutes of compile per new shape (fix resolution, layer count and steps; pad text); torch_xla lags torch (seen: torch 2.11 vs torch_xla 2.9). **Speed estimate:** v5e-8 about 50–70 s at 50 steps or 30–40 s at 30 steps; v6e-8 about 12–20 s at 50 steps [est].

## 4. Matting, segmentation and helper tools

VRAM column: "estimate" means it was inferred from parameter counts and file sizes. None of these were run on a T4.

| Model | License | Free-hostable where | VRAM fit on T4 16 GB | Layer capability | HF link |
|---|---|---|---|---|---|
| LayerDiffuse SD1.5 / SDXL | Code Apache-2.0; weights CreativeML OpenRAIL-M; diffusers port MIT | Kaggle, Colab (notebook use), Modal | Yes. SD1.5 is about 4 GB and SDXL about 7 GB fp16; SDXL has a `--cpu-offload` flag (estimate) | Native text-to-RGBA foreground; SD1.5 also does joint fg+bg+blend and fg-given-bg | [layerdiffusion-v1](https://huggingface.co/LayerDiffusion/layerdiffusion-v1) |
| Qwen-Image-2.1 | Qwen Research License (non-commercial) | Kaggle, Colab, Modal | Likely, with Q8 GGUF denoiser (7.64 GB) plus Q4 text encoder (about 5 GB), or with offload (estimate) | Native text-to-RGBA, transparent layer editing, subject extraction | [Qwen/Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1) |
| FLUX.2 Klein 4B | Apache-2.0 | Kaggle, Colab, Modal | Yes. The card says "as little as 13GB" | None; needs matting afterwards | [FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| FLUX 3 Image Klein (5.6B) | FLUX Kommunity License v1.0 (free commercial use under $5M revenue); gated | Kaggle, Modal | Hard. Card peak is about 25–31 GB at 1024 px; would need INT8 plus encoder offload, and T4 has no FP8/NVFP4 acceleration (estimate) | None; needs matting afterwards | [flux-3-image-klein](https://huggingface.co/black-forest-labs/flux-3-image-klein) |
| Qwen-Image-Layered (20B) | Apache-2.0 | Kaggle only, maybe; Colab free fails on RAM | No at BF16 (about 40 GB). A 4-bit SDNQ/GGUF with offload is unproven | Image-to-layers only; no text-to-layers weights found | [Qwen/Qwen-Image-Layered](https://huggingface.co/Qwen/Qwen-Image-Layered) |
| LayerDiffuse-Flux | Repo shows no LICENSE; HF labels the weights afl-3.0; inherits FLUX.1-dev non-commercial | Kaggle (about 29 GB RAM) | Only with heavy quantization or offload (estimate) | Native RGBA on FLUX.1-dev | [RedAIGC/Flux-version-LayerDiffuse](https://huggingface.co/RedAIGC/Flux-version-LayerDiffuse) |
| CLD | MIT code; FLUX.1-dev non-commercial base | Kaggle | Only with quantization or offload (estimate) | Layer decomposition | [thuteam/CLD](https://huggingface.co/thuteam/CLD) |
| LayerD | Apache-2.0 code (repo archived) | Anywhere, including CPU and ZeroGPU | Yes; BiRefNet-based (estimate) | Graphic-design image-to-layers | [cyberagent/layerd-birefnet](https://huggingface.co/cyberagent/layerd-birefnet) |
| BiRefNet | MIT | Anywhere, including CPU and ZeroGPU | Yes (0.2B) | Cut-out matting | [ZhengPeng7/BiRefNet](https://huggingface.co/ZhengPeng7/BiRefNet) |
| BEN2 base | MIT (the Full model is API-only) | Anywhere, including CPU | Yes (94.6M) | Cut-out matting | [PramaLLC/BEN2](https://huggingface.co/PramaLLC/BEN2) |
| SAM 2.1 | Apache-2.0, not gated | Anywhere | Yes (39M–224M) | Prompted segmentation | [GitHub](https://github.com/facebookresearch/sam2) |
| Florence-2-large | MIT | Anywhere | Yes (0.77B) | Text grounding and detection to drive SAM | [microsoft/Florence-2-large](https://huggingface.co/microsoft/Florence-2-large) |
| LaMa | Apache-2.0 | Anywhere, including CPU | Yes | Background fill behind removed objects | [smartywu/big-lama](https://huggingface.co/smartywu/big-lama) |
| RMBG-2.0 | CC BY-NC 4.0, gated | Anywhere | Yes | Matting (non-commercial) | [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) |
| SAM 3 | Custom Meta licence, gated | ZeroGPU, Kaggle | Likely (about 3.6 GB F32 weights) | Text-prompted segmentation | [facebook/sam3](https://huggingface.co/facebook/sam3) |

### Ruled out and why
- **Unreleased or withdrawn layered methods** (ART, OmniPSD, PSDiffusion, DreamLayer, LayerFusion, RefLayer, DiffDecompose, LiWi, LASAGNA, LayerDecomp): [papers-survey.md §2](papers-survey.md#2-methods-we-cannot-run-no-weights-or-code).
- **RMBG-2.0** (CC BY-NC 4.0, gated): BiRefNet has the same architecture under MIT. **ObjectClear** (NTU S-Lab, non-commercial). **OmniEraser** (a FLUX.1-dev finetune, so effectively non-commercial).
- **IC-Light v2:** weights unreleased, announced as non-commercial (v1 is what we run).
- **Colab tunnelling:** banned by the Colab FAQ on free runtimes.
- **pix2gestalt** (amodal completion): not needed when objects are generated whole; hidden parts are filled by SDXL-inpaint or Qwen-2.1 instead ([../models/amodal-fill.md](../models/amodal-fill.md)).

Since then ART+ weights were found (the ART base LoRA is byte-identical to the Apache-2.0 `thuteam/CLD` file) and run on our T4s, and Qwen-Image-Layered, LayerDiffuse-Flux and CLD turned out to fit on 2× T4.

## 5. Licences that matter (non-commercial project)
FLUX.1-dev (non-commercial) for RevealLayer, ART+, CLD, LayerDiffuse-Flux; Qwen Research licence for Qwen-Image-2.1; Stability Community licence for Stable-Layers; Apache-2.0 for Qwen-Image-Layered, IC-Light v1, SAM2, LaMa; OpenRAIL-M for LayerDiffuse weights. All fine for this personal, non-commercial project.
