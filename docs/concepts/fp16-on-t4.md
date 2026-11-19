# Running bf16 models on fp16 GPUs (T4): `fp16_mixed`

> **Role: concept (stable explanation).** How it works and why. Current numbers live in [../status.md](../status.md) and the factsheets in [../models/](../models/README.md); history in [../log.md](../log.md).

## The problem
Kaggle's free T4 has fast **fp16** (19 TFLOPS) but no fast bf16 (2 TFLOPS emulated; fp32 3.7). Models trained in bf16 (Qwen-Image family, FLUX) produce internal values above fp16's limit of 65504; one overflow becomes inf/NaN and spreads, so the output is all-NaN, black or noise. ComfyUI lists Qwen-Image as bf16/fp32 only. Patching single layers (LayerNorm in fp32, splitting blocks) only moved the failure to the next op.

## The fix: [`../../prototype/layerproto/fp16_mixed.py`](../../prototype/layerproto/fp16_mixed.py)
- **Every Linear:** scale the input down to absmax 32, multiply in fp16 (fast tensor cores), scale the result back in fp32; if that call is still non-finite, redo it in fp32. (Absmax 1024 still gave NaNs.)
- **Attention (Qwen-Image):** q/k in fp16 (RMS-normalised, small), v scaled the same way (attention is linear in v). Skipped automatically for models whose diffusers has no Qwen module.
- **Everything else** (residual stream, norms, gates, embeddings) in fp32; the model output is returned in fp16 so pipelines are unchanged.
- **LoRAs unmerged:** `add_lora` / `remove_lora` attach PEFT, kohya and diffusers LoRAs next to GGUF weights (which cannot be merged); convert BFL/kohya FLUX keys to diffusers names first.

```python
from layerproto.fp16_mixed import apply_fp16_mixed, add_lora
apply_fp16_mixed(transformer)            # once, after loading
add_lora(transformer, "lora.safetensors", scale=1.0)
```

## Other fp16 hazards found
- **GGUF non-Linear parameters:** diffusers' GGUF loader only dequantises Linear layers; other parameters keep packed bytes (Qwen-Image-Layered `addition_t_embedding`, a Qwen-Image-2.1 parameter → "4096 vs 8192"). Dequantise them once after loading (`qwen_layered.fix_gguf_non_linear`).
- **Attention masks filled with −1e9 or `finfo(fp16).min`:** become −inf in fp16 (fully masked rows → NaN). Use −1e4. (RevealLayer.)
- **Unguarded residuals and fp16 VAE decodes** (RevealLayer's refiner, its "odd purple output" VAE). Decode in fp32.
- **VAEs:** Qwen-Image-2.1's stock VAE gives NaNs in fp16 on transparent pixels; `madebyollin/texture-fix-vae-for-qwen-image-2.1` is fp16-safe.

## What we learned about FLUX
Plain FLUX.1-dev GGUF Q4 runs cleanly in plain fp16 on a T4 (41 s for 16 steps at 512 px, zero non-finite values): diffusers already clamps the single-block residuals. Breakage in FLUX-based layer models came from their own code. Sources: [../../research_notes/Layered loop open paths/flux_layered_t4_and_weights.md](../../research_notes/Layered%20loop%20open%20paths/flux_layered_t4_and_weights.md).

**Several LoRAs on GGUF weights:** `fp16_mixed.add_lora` keeps a list per module and adds every delta; until 2026-11-10 it overwrote, so multi-LoRA models (ART+) silently ran with only the last LoRA.
