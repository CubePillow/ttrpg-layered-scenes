# Qwen-Image-2.1: sources (RGBA design, prompts, speed, licence)

Research date 2026-11-09. Read: HF card and Space `app.py`, GitHub README/tree, `prompt_rewrite/pe_core.py`, diffusers `pipeline_qwenimage21.py`, HF LICENSE, Comfy docs, Unsloth GGUF card, HF discussions #6 / #32 / #35, the madebyollin texture-fix VAE card. Not found: a tech report, an official DashScope page, usable blog text. Our measurements and decisions: [docs/models/qwen-image-2.1.md](../../docs/models/qwen-image-2.1.md).

## 1. Design and official code paths

- **RGBA is native:** the VAE takes 4-channel RGBA in and out and encodes to a 64-channel latent at 16× compression ([README](https://github.com/QwenLM/Qwen-Image-2.1)); generation and editing share one pipeline. One call returns one image; the repo, Space and pipeline have **no decomposition, extraction or mask mode** (the README only says it can "edit transparent layers" and "extract subjects").
- **Only official prompt:** the transparent-generation wrapper "This is an RGBA image with transparency. xxxxx The image has alpha channel and the background is transparent." ([Space app.py](https://huggingface.co/spaces/Qwen/Qwen-Image-2.1/raw/main/app.py), HF card). ComfyUI's background-removal template uses "Remove the background, and output a PNG image." ([Comfy docs](https://docs.comfy.org/tutorials/image/qwen/qwen-image-2-1)).
- **Condition images (diffusers):** all converted to RGBA and read by the VAE on four channels; only the Qwen3-VL vision-encoder copy is alpha-composited over white; no mask argument (circles and masks are just images); the output aspect ratio follows the **last** image; no bbox or position arguments ([pipeline](https://raw.githubusercontent.com/huggingface/diffusers/main/src/diffusers/pipelines/qwenimage21/pipeline_qwenimage21.py)).
- **Space defaults:** 40 steps, 1024 px "speed" or 2048 px "quality", negative prompt " ", true-CFG 1.0, KV cache only if it fits 10 GB; edit mode is triggered by the presence of images.
- **Prompt rewriter (`pe_core.py`):** profiles `t2i` and `edit`; edit output `{"rewritten_prompt", "wh_ratio", "ratio_follow": "<image1>"}`; references are `<image1>`, `<image2>` in input order; the system prompts live in the checkpoints. The rewriter can add unrequested detail, so switch it off for precise prompts and state what must stay unchanged.
- **ComfyUI nodes:** "Text Encode Qwen Image 2.1" has 16 reference slots, templates wire 10, `image_1` is the image being edited; SplitImageWithAlpha / JoinImageWithAlpha (mask 1 = transparent); 3-channel nodes downstream may error on RGBA.
- **Local edits** are circle- or mask-guided (remove a watch, recolour hair); **multi-reference** up to 10 images ("These three characters are sitting around a campfire"). Placement is by prompt and circle/mask images only. Harmonising a pasted object by passing the composite as `image_1` is plausible; we tested it ([relocate-harmonise.md](../../docs/models/relocate-harmonise.md)).
- Training data is not disclosed. Hosted APIs (Krea, RunComfy) expose `background: transparent|opaque`.

## 2. Alpha quality (no measured benchmark exists)

- Runware's guide (its "Pro" endpoint, may differ from the open weights): alpha is "subject or nothing" (a glass bottle about 99 % opaque), pale fringes on dark backgrounds, shadows and floors must be excluded by name ("no floor and no shadow"), JPG drops alpha. Vendor samples look clean; hair, glass, fur and motion blur are reported hard (snippet-level, unverified).
- Official benchmark: only VDEBench text editing (0.81 local, 0.83 global). No comparison with LayerDiffuse, Qwen-Image-Layered or ART found; for reference Qwen-Image-Layered beats LayerD on alpha soft-IoU ([alphaxiv 2512.15603](https://alphaxiv.org/resources/2512.15603v1)).

## 3. Speed, memory, fp16

- **Community numbers:** RTX 4060 Ti 16 GB, INT8 DiT + text encoder, 1024², 25 steps: about 20 s per generation, about 60 s per edit, about 15 GB peak ([disc #35](https://huggingface.co/Qwen/Qwen-Image-2.1/discussions/35)). RTX 5090 NF4: 15.2 GB peak at 1024², 19.1 GB with two references; 40 steps 19.2 s at 1024², 118.8 s at 2048² (time about 6× for 4× pixels) ([disc #32](https://huggingface.co/Qwen/Qwen-Image-2.1/discussions/32)). Two references add about 4 GB.
- **KV cache (Comfy):** `int8` (half the size, about bf16 accuracy) or `int4` (a quarter, about 2× per-step error). Steps: base 25, Turbo 8, Lightning 4; local edits are fine at 4-8, full-frame edits need about 25.
- **Accelerators:** Turbo checkpoint / LoRA (rank about 178), 8 steps CFG 1; LightX2V Lightning 4-step LoRA (about 67 MB, 2026-10-13) and Lightning v2 RL (a full distilled transformer, 2026-11-02); Alibaba PAI Fun-Acc 4-step LoRA (346 MB). Not verified on HF directly.
- **GGUF (Unsloth):** Q2_K 2.47 GB, **Q4_K_S 3.91**, Q4_K_M 4.2, Q5_K_M 5.39, Q8_0 7.64, F16 14.2 GB; text encoder `Qwen3-VL-8B-Instruct-UD-Q4_K_XL.gguf` (LPIPS 0.029 against Q4_K_M); Unsloth's about-11-GB figure is an estimate. City96's ComfyUI-GGUF support is disputed ("Unknown model architecture", use the leejet fork). We load the GGUF with diffusers and dequantise a leftover packed parameter ([fp16-on-t4.md](../../docs/concepts/fp16-on-t4.md)).
- **fp16:** the stock VAE decoder NaNs in fp16 mostly on fully transparent regions (max activation about 3.5M against the fp16 limit 65504). The **texture-fix VAE** cuts it to about 1.3k with 0 NaN in the stress tests; rFID 3.38 → 2.06, PSNR 33.29 → 32.79; load `AutoencoderKLQwenImage21` from that repo and pass `vae=`. Earlier Qwen-Image DiTs gave NaN latents in fp16 in ComfyUI ([#10751](https://github.com/Comfy-Org/ComfyUI/issues/10751)); one report of an all-NaN text encoder on an RTX 3070 even in bf16/fp32, suspected corrupt files ([Turbo disc #6](https://huggingface.co/Qwen/Qwen-Image-2.1-Turbo/discussions/6)). No T4 report was found.

## 4. Decomposition

No official multi-layer mode for 2.1 and no announced "Qwen-Image-Layered 2.x"; no community decomposition LoRA on 2.1. Qwen-Image-Layered (2025-12-19, Apache-2.0, 3-8 layers, recursive) remains the only Qwen decomposer; the LoRA-based decomposition papers found target it, not 2.1 ([arXiv 2603.14925](https://arxiv.org/pdf/2603.14925); MRT claims to beat it on many-layer flat designs, [2605.27235](https://arxiv.org/pdf/2605.27235)).

## 5. Licence ([LICENSE](https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE))

Non-commercial grant, "for research or evaluation purposes only" (§1i, §2a); commercial licences from model-business@notice.qwencloud.com (§2b). If you distribute: include the licence, mark changes, add a NOTICE (§3); derived models must show "Built with Qwen" (§4b); "Qwen" cannot be the primary product name (§4c). Output ownership is not addressed; Chinese law, courts in Hangzhou (§8); breach means deleting the Materials (§7b). A free personal prototype fits a permissive reading. Contrast: Qwen-Image-Layered is Apache-2.0.
