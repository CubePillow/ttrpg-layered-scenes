# Multi-turn edit drift and consistency: evaluation sources (as of Nov 2026)

Source notes for [docs/research/drift-evaluation.md](../../docs/research/drift-evaluation.md); our harness is `prototype/layerproto/drift_eval.py` (3 arms, metrics outside the edited regions). Numbers come from arXiv HTML or alphaxiv text of the primary papers; items from secondary summaries are marked [unverified].

## 1. Multi-turn editing benchmarks: what they measure

Drift is well documented for flat editors: consistency of unedited content falls with every turn, and strong single-turn editors collapse fastest. Benchmarks run 3 turns (EdiVal), 5 (MSE-Bench), 8 (MTEdit), 10+ (TailSteer, AnchorEdit). None includes a layered editor.

- **EdiVal-Agent (ICLR 2026, [arXiv 2509.13399](https://arxiv.org/abs/2509.13399)):** content consistency EdiVal-CC = ½ × (background similarity outside every object box ever seen + mean similarity of unchanged-object crops), similarity by DINOv3 (preferred over L1, which small shifts inflate); quality by HPSv3; 3 turns, 16 editors. Every editor loses about 3-4 points per turn:

  | Editor | T1 | T2 | T3 |
  |---|---|---|---|
  | FLUX.1-Kontext-dev | 95.32 | 92.24 | 90.22 |
  | GPT-Image-1.5 | 94.49 | 91.20 | 88.49 |
  | Nano Banana | 93.91 | 90.48 | 89.48 |
  | Seedream 4.0 | 92.51 | 88.03 | 85.86 |
  | Qwen-Image-Edit | 84.22 | 80.52 | 77.98 |
  | GPT-Image-1 | 81.00 | 77.78 | 75.50 |

  Qwen-Image-Edit's overall score falls 78.36 → 59.56 → 41.93 (exposure bias); flow-matching editors brighten progressively (FLUX Kontext excepted); HPSv3 falls while a VLM judge's quality scores stay high, so VLM judges miss quality drift.
- **MSE-Bench (VINCIE, [2506.10941](https://arxiv.org/pdf/2506.10941)):** 100 five-turn sessions, GPT-4o judges. Success per turn T1 → T5 (AnchorEdit paper): JoyImage-Edit .980 → .446, VINCIE .950 → .487, AnchorEdit .950 → .567: success roughly halves over 5 turns.
- **MTEdit-Bench ([2610.23751](https://arxiv.org/html/2610.23751)):** 100 eight-turn samples, VLM judge scores IF and CC 0-10, a trajectory fails below 6; turn-8 IF/CC: Nano Banana Pro 8.83/7.51, GPT Image 2 7.11/5.81, FLUX.1-kontext-dev 2.13/1.76; VINCIE, OmniGen2 and Lance about 0.
- **TailSteer "Add & Preserve" ([2611.06741](https://arxiv.org/html/2611.06741)):** 100 images, a red box, 10 sequential add/remove edits inside it, PSNR/SSIM/LPIPS outside the box against the original plus object accuracy inside. The closest design to a layered "edit one object, keep the rest" test. Turn-10 outside PSNR: Qwen Image-2.1 16.93 dB, FLUX.1 Kontext dev 18.64, GPT-Image-2.5 18.55, FLUX.2 Klein 13.85: under 19 dB even for the best. Paper is CC BY-NC-SA; code release unconfirmed.
- **Omni IIE Bench ([2603.16944](https://arxiv.org/abs/2603.16944)):** 260 dialogues of about 4.35 turns; background LPIPS single → multi-turn: MGIE 0.294 → 0.580, Qwen-image-edit 0.327 → 0.390, FLUX 0.428 → 0.478, Step1X 0.259 → 0.344 ("a substantial drop in background preservation across all models").
- **Multi-Edit Bench / layer-wise memory ([2505.01079](https://arxiv.org/html/2505.01079)):** 2-5 sequential edits on 3-6-layer scenes; inpainting baselines decline after three steps; the per-step plot exists only as a figure.
- Others seen: AnchorEdit ([2606.11751](https://arxiv.org/abs/2606.11751)), MagicBrush (final-image-only multi-turn), ICE-Bench (single-turn), MIRA (an agent, not a benchmark).

## 2. Metrics

Flat images: masked or region-excluded similarity (DINOv3 in EdiVal-CC; PSNR/SSIM/LPIPS outside the edit region in TailSteer); identity by DreamSim with the background removed (ConsiStory) or masked patch metrics (MaSC, ID-Sim). Layered papers measure single-shot decomposition: alpha-weighted RGB L1 and alpha soft IoU with LayerD's DTW-aligned protocol (Qwen-Image-Layered on Crello: L1 0.0594 / IoU 0.8705 against LayerD 0.0709 / 0.7520 [unverified]); compositing is standard alpha-over. **None measures recomposition error over cycles.** ViStoryBench (CVPR 2026, Apache-2.0 code, MIT data) is the template for identity: detect and crop characters, then identity (CIDS) and style (CSD) similarity; it expects its own directory layout.

## 3. Layered versus flat: the gap

No independent multi-turn layered-versus-flat study exists. Qwen-Image-Layered gives only qualitative single-edit comparisons. **LimeCross ([2605.10319](https://arxiv.org/html/2605.10319))** keeps an explicit RGBA representation across edits, never re-flattened; baselines fed their own composites "accumulate errors", shown only qualitatively. Table 1 (6,000 2-3-layer sequences): preservation PSNR ∞ by construction (trivial) against MagicQuillV2 21.75 and KV-Edit 20.49; ImageReward 0.493 / 0.421 / 0.278. It does not measure error growth against step count or repeated decomposition. LayerD's error accumulation is within one decomposition, not across edit cycles. No paper measures decompose → recompose stability over cycles (our arm C).

## 4. Compute reference and reusable code

- No T4 benchmark for Kontext-dev or Qwen-Image-Edit in GGUF. Nearest: FLUX dev 1024², 20 steps about 32 s on an RTX 3060 12 GB (Q5), 90-150 s at Q4_K_S low-VRAM on an 8 GB card; Kontext-dev about 9 s per edit on an RTX 4090 (NF4). Estimate for the T4: Kontext Q4/Q5 at 1024² 60-120 s per edit (512-768 px 2-3× faster); a 5-edit timing pilot should come first.
- **EdiVal** (`tianyucodings/EdiVal`, data `C-Tianyu/EdiVal`): a custom editor plugs in through a class with `generate_single_edit`; `eval.py` computes IF and CC with GroundingDINO + DINOv3; instruction generation needs an OpenAI key but a hand-written instruction CSV works; licence badges conflict (MIT / CC BY-SA 4.0), check LICENSE. Direct reuse: wrap the layer stack and the flat editor as editor classes, MAX_TURNS raised to 10.
- Fine for a personal non-commercial project; BY-SA / NC terms would bind redistributed derived data.

## 5. Protocol chosen

EdiVal harness as backbone with our own instruction CSV; 10 turns (plus a 20-turn subset); TailSteer-style outside-region PSNR/SSIM/LPIPS against turn 0; per-layer alpha IoU and alpha-weighted L1; arm C re-decomposes the composite every turn and logs layer-matching IoU against the turn-0 layers (a novel measurement); report curves, area under the curve and the turn at which outside PSNR first drops below 25 dB.
