# Hosting options considered and parked (moved from hosting.md, 2026-11-11)

> **Role: ideas considered, not used.** Paid APIs and cost estimates for Qwen-Image-Layered, university GPU access (LMU / LRZ: how to get access, questions to ask), and the base text-to-image models, hosted image APIs, prices (snapshot 2026-11-05), hosted test links and free browser generators. The current setup (free Kaggle 2x T4, started from the app) is in [hosting.md](../research/hosting.md).

## Qwen-Image-Layered: speed and API cost
- Official settings: 640 px, 50 steps, CFG 4. No published per-GPU timings; no Lightning for Layered.
- On our free 2× T4: 35 min at defaults, **27–35 s** at 384 px / 4 layers / 4 steps / CFG 1 ([../models/qwen-image-layered.md](../models/qwen-image-layered.md)).
- Hosted: fal about **$0.05 per image** (28 steps default); WaveSpeed $0.025 base (scales with layers); 302.ai about $0.05. €100 ≈ 2,000 runs: suits final demos more than prototyping.

### Paid APIs vs university GPUs (for about 2,000 Qwen-Image-Layered runs)

| Option | Cost for 2,000 runs | Latency per run | Setup effort | Terms |
|---|---|---|---|---|
| fal.ai (~$0.05/run) [U price] | ~$100 | ~10 to 60 s [U] | Minutes: API key and Python client | Commercial ToS; your images go to a third party. Fine for a personal or non-commercial project. |
| WaveSpeed ($0.025/layer) [U price] | 4 layers ≈ $0.10/run, so ~$200 | similar [U] | Minutes | Same as fal.ai |
| RBG abakus | Free | Queue wait, then ~2 to 4 min if A100-class [U] | Email the RBG with an advisor confirmation; days | Institute rules; academic use only |
| LRZ AI Systems | Free | Queue (can be hours), then ~1.5 to 4 min | Needs a PI's AI-enabled project; days to weeks. Enroot container build. | Research-focus requirement |

Bottom line: for a course prototype with about 2,000 runs, a paid API costs $100 to $200 and works within the hour. The university GPUs are free but depend on a supervisor and take setup time. They become worth it for a recurring or larger workload, or for fine-tuning.

### Speed estimate per GPU (FLOPs-based, 640 px, 4 layers, CFG, 50 steps)

Assumptions: 6.6e14 FLOPs per step (640 px, 4 layers, with CFG) and 50 steps, giving 3.3e16 FLOPs per run.

| GPU | Peak | Assumed effective | s/step | s/run (50 steps) | 2,000 runs |
|---|---|---|---|---|---|
| T4 (measured) | 65 fp16 | 19 TFLOPS | ~35 | ~29 min | ~970 h |
| A100 bf16 | 312 | ~150 (about 50% MFU) | ~4.4 | ~3.7 min | ~122 h |
| H100 bf16 | ~990 | ~400 (about 40% MFU) | ~1.7 | ~1.4 min | ~46 h |

The T4 is also too small for bf16 (16 GB, compute capability 7.5), so on a T4 you need 4-bit plus offloading, which makes it slower still. An A100 40 GB is tight for bf16, so an 80 GB A100 or an H100 is preferable. Inference with fewer steps (for example 20 to 30) cuts these times proportionally.

## LMU and LRZ access

| Route | Hardware | Access | Notes |
|---|---|---|---|
| RBG Slurm (institute) | CIP pool, RTX 2060 SUPER 8 GB (partition `NvidiaAll`) | all students and staff, no registration; 15 running / 30 submitted jobs | jobs pause when someone uses the machine |
| RBG abakus servers | stronger cards (A5000 24 GB per earlier research [U]) | mail rbg@ifi.lmu.de with a good reason + advisor confirmation; `srun -q abaki -p Abaki …`; default runtime 1 day | GPU models not listed publicly |
| LRZ AI Systems | P100 / V100 / A100 / H100 | valid LRZ account + AI-enabled project with research focus; master user adds you to `<projectID>-ai-c`; Slurm + Enroot | projects renewed yearly; BayernKI as alternative route |
| MCML [U] | DGX / A100 / H100 at LRZ | via an MCML PI | not verified on a public page |
| NHR@FAU (Alex) [U] | A100 / A40 | free NHR-Starter projects via a PI | better fit than Gauss for small jobs |
| Gauss Centre [U] | JUWELS, SuperMUC-NG | proposals for large projects | overkill |

Access to the RBG and LRZ machines needs a supervisor's confirmation or an AI-enabled LRZ project; the step-by-step and the questions to ask were removed 2026-11-11 (course-specific; reference repository).

## Base text-to-image models and image APIs

Candidates for the "whole scene first" step (the current choice is SDXL-Turbo, [../models/sdxl-turbo.md](../models/sdxl-turbo.md)) and for sketch input.

### Hosted image APIs (prices per 1024 px image, 2026-11-05)

| Provider / model | Price per 1024 px image | Notes |
|---|---|---|
| DeepSeek API | n/a | Text-only models (V4-Pro, V4-Flash). Janus-Pro is self-host only |
| Kimi (Moonshot) API | n/a | Vision models only read images |
| Cloudflare Workers AI, FLUX.1 schnell | About $0.00063 (≈ 58 neurons per image [est]) | Free 10,000 neurons/day, so about 170 images/day by arithmetic; some guides say 20–50 |
| Together AI, FLUX.1 schnell | $0.0027 | OpenAI-style client |
| fal / Replicate, FLUX.1 schnell | $0.003 per megapixel | |
| Runware | From $0.0006 | Cheapest at volume |
| fal, Z-Image Turbo (text-to-image and image-to-image) | $0.005 per megapixel | Image-to-image has a `strength` setting |
| WaveSpeed, Z-Image Turbo | $0.005; $0.01 with ControlNet | |
| fal, FLUX 3 Image Klein | $0.009 per 1K image (generation and edit) | |
| OpenRouter, FLUX.2 Klein 4B | About $0.014 (measured by OpenRouter) | |
| OpenAI GPT Image 2 | $0.006 at low/default quality, $0.211 at high | OpenRouter's test: default billed the same as low |
| Alibaba Qwen Image 2.1 Turbo / ByteDance Seedream 5.0 Flash | $0.014–0.018 | Separate accounts and regions |
| Google Nano Banana (Gemini 2.5 Flash Image) | $0.039 ($0.0195 batch) | |

**Routers:**
- **LiteLLM** (MIT, free) gives one interface over OpenAI, Azure, Google AI Studio, Vertex AI, Bedrock, Black Forest Labs, Recraft, OpenRouter and any OpenAI-compatible endpoint. Worth it only when routing between several providers.
- **OpenRouter** passes model prices through and returns the exact billed amount in `usage.cost`. Sensible while comparing models; once one model is chosen, its provider's own key avoids the fee.

### Price-to-performance (arena Elo vs price)

**Data:** Artificial Analysis text-to-image arena (blind pairwise votes, Elo), 101 models with a price, at 1024×1024 on the creator's API with default settings.

**Method:** the Pareto frontier of price against rating (+50 Elo is about 57 % blind-vote wins; steps under about 25 Elo are noise). Elo per dollar and a fitted price-quality line were rejected (they reward the cheapest model or measure model age).

| Model | Elo | $/1,000 | Step from previous | Verdict |
|---|---|---|---|---|
| P-Image-Ideogram (Very Low) | 909 | 3.0 | — | Cheapest floor |
| FLUX.2 [dev] Flash | 988 | 5.0 | +79 for +$2 | Good step |
| FLUX.2 [dev] Turbo | 995 | 8.0 | +7 for +$3 | Within noise |
| FLUX 3 Image Klein | 1043 | 9.0 | +48 for +$1 | Good step; open weights |
| Muse Image | 1127 | 10.0 | +84 for +$1 | Knee of the curve |
| Nano Banana 2.1 | 1176 | 33.6 | +49 for +$23.6 (3.4× price) | Diminishing returns |
| GPT Image 2.5 Sunburst (max) | 1223 | 210.7 | +47 for +$177 (6.3× price) | Quality at any cost |


**Limits:** arena Elo reflects general prompts, not sketches; prices are defaults at 1024 px; cheaper quality tiers are not benchmarked.

### Sketch + prompt: three ways in

Text-to-image models take only a prompt, so a sketch needs one of these:

| Method | How the sketch is used | Behaviour |
|---|---|---|
| **Plain image-to-image** | The sketch is noised, then redrawn. One "strength" setting | Trades faithfulness against realism. Sparse black lines on white tend to come out as a pale sketch or get ignored |
| **ControlNet (scribble / lineart)** | Lines constrain structure through the whole generation; the prompt decides appearance | The established, most predictable method |
| **Reference-image editing** | The sketch is a reference image with an instruction ("turn this sketch into…") | Looser composition, often understands rough drawings better. Regenerates from scratch rather than partially redrawing |

### Self-hostable or cheaply hosted models

| Model / combination | Sketch method | Kaggle 16 GB / LMU 8 GB | Cheapest hosted | License | Try it |
|---|---|---|---|---|---|
| **SDXL + scribble ControlNet** | ControlNet (any line type and width); img2img; inpainting | Yes / yes | About $0.0013/image (base SDXL, fal) | CreativeML Open RAIL++-M; ControlNet Apache-2.0 | [Scribble SDXL Flash Space](https://huggingface.co/spaces/linoyts/scribble-sdxl-flash) · [ControlNet](https://huggingface.co/xinsir/controlnet-scribble-sdxl-1.0) · [Base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) |
| **Z-Image Turbo (6B) + union ControlNet** | ControlNet with scribble (since the 2601 release); img2img (`strength`, default 0.6); inpainting | Yes (developers: fits within 16 GB) / quantized only [est] | $0.005/image; $0.01 with ControlNet (WaveSpeed) | Apache-2.0 | [Official Space](https://huggingface.co/spaces/Tongyi-MAI/Z-Image-Turbo) · [mrfakename Space](https://huggingface.co/spaces/mrfakename/Z-Image-Turbo) · [Model](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) · [ControlNet](https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.1) |
| **FLUX.2 Klein 4B** | Reference images / editing | Yes (card: about 13 GB) / borderline with FP8 [est] | About $0.014 (OpenRouter); $0.0006–0.002 (Runware) | Apache-2.0 | [Official Space](https://huggingface.co/spaces/black-forest-labs/FLUX.2-klein-4B) · [Model](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| **FLUX 3 Image Klein (5.6B)** | Reference editing (up to 10 references, bounding boxes); sketch input untested | INT8 build runs on 8 GB RTX cards (BFL blog) | $0.009 per 1K image (fal) | FLUX Kommunity v1.0 (free under $5M revenue), gated | [Model](https://huggingface.co/black-forest-labs/flux-3-image-klein) · [fal edit](https://fal.ai/models/blackforestlabs/flux-3/klein/edit-image) |
| **Qwen-Image-2.1 + union ControlNet** | ControlNet with scribble and lineart; inpainting | Tight, with offloading / no | No official API | Qwen Research License (non-commercial); ControlNet research license | [Model](https://huggingface.co/Qwen/Qwen-Image-2.1) · [ControlNet](https://huggingface.co/alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union) |
| FLUX.1 schnell (drafts only) | None verified | n/a | Cloudflare free daily | Apache-2.0 | [Model](https://huggingface.co/black-forest-labs/FLUX.1-schnell) |

Dropped: Fibo 2.0 (CC BY-NC 4.0, about 16 GB for weights alone) and Ideogram 4.0 (non-commercial, needs a 24 GB GPU or heavy 4-bit offloading). Both are beaten by FLUX 3 Klein on price and quality, and neither has a sketch ControlNet.
