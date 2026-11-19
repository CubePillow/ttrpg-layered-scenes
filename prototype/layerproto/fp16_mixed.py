"""Run the Qwen-Image(-Layered) transformer on GPUs without bf16 (Kaggle T4, P100, RTX 20xx) without NaNs.

Qwen-Image is trained for bf16; its hidden values exceed the fp16 limit (65504), so a plain fp16 run gives all-NaN
latents (ComfyUI also lists Qwen-Image as bf16/fp32 only). This keeps the fast fp16 tensor-core matmuls but holds
everything else in fp32:

  * every Linear: input scaled down to absmax 32, fp16 matmul, result scaled back in fp32
    (falls back to a fp32 matmul for that call if the fp16 result is still non-finite)
  * attention: q/k in fp16 (RMS-normalised, small), v scaled the same way (attention is linear in v)
  * residual stream, norms, gates, embeddings: fp32
  * the model's output is returned in fp16, so the diffusers pipeline is unchanged

Measured on Kaggle 2x T4 (Q4_K_S GGUF, 640 px, 4 layers): no NaN, 42 s/step, peak 8.8 / 8.4 GB.

    from layerproto.fp16_mixed import apply_fp16_mixed
    apply_fp16_mixed(transformer)        # once, after loading; idempotent
"""
import types

import torch
import torch.nn.functional as F

LINEAR_LIMIT = 32.0  # absmax the fp16 matmul input is scaled to (1024 was still too high: NaNs)
ATTN_LIMIT = 32.0


def _dequant(w):
    if type(w).__name__ == "GGUFParameter":
        from diffusers.quantizers.gguf.utils import dequantize_gguf_tensor
        return dequantize_gguf_tensor(w)
    return w


def _mixed_linear(self, x):
    x = x.float()
    s = (x.abs().amax() / LINEAR_LIMIT).clamp_(min=1.0)
    y = self._fp16_orig_forward((x / s).to(torch.float16)).float()   # = W x/s + b
    b = getattr(self, "bias", None)
    if not torch.isfinite(y).all():                                  # rare: this call in fp32
        y = F.linear(x, _dequant(self.weight).float(), None if b is None else b.float())
    elif b is None:
        y = y * s
    else:
        b = b.float()
        y = (y - b) * s + b
    loras = getattr(self, "_fp16_lora", None)
    if loras:                                                        # low-rank deltas (stacked LoRAs), same input scaling
        xs = (x / s).to(torch.float16)
        for i, (A, B, k) in enumerate(loras):
            if A.device != x.device:                                 # module was moved (e.g. split over GPUs)
                A, B = A.to(x.device), B.to(x.device)
                loras[i] = (A, B, k)
            y = y + F.linear(F.linear(xs, A), B).float() * (s * k)
    return y


def _lora_pairs(sd):
    """{module name: (A [r, in], B [out, r], alpha or None)} for common LoRA key layouts (PEFT / kohya / diffusers)."""
    out = {}
    for key in sd:
        for a_suf, b_suf in ((".lora_A.weight", ".lora_B.weight"), (".lora_down.weight", ".lora_up.weight"),
                             (".lora_A.default.weight", ".lora_B.default.weight")):
            if key.endswith(a_suf):
                base = key[: -len(a_suf)]
                bkey = base + b_suf
                if bkey in sd:
                    alpha = sd.get(base + ".alpha")
                    name = base
                    for pre in ("base_model.model.", "diffusion_model.", "transformer.", "model."):
                        if name.startswith(pre):
                            name = name[len(pre):]
                    out[name] = (sd[key], sd[bkey], None if alpha is None else float(alpha))
    return out


def add_lora(model, path_or_state_dict, scale: float = 1.0):
    """Attach a LoRA to an fp16_mixed-patched model (works with GGUF-quantised linears, nothing is merged).
    Returns (matched modules, LoRA modules not found)."""
    sd = path_or_state_dict
    if isinstance(sd, str):
        from safetensors.torch import load_file
        sd = load_file(sd)
    pairs = _lora_pairs(sd)
    mods = dict(model.named_modules())
    hit, miss = 0, []
    for name, (A, B, alpha) in pairs.items():
        m = mods.get(name)
        if m is None or not hasattr(m, "_fp16_orig_forward"):
            miss.append(name)
            continue
        dev = next((p.device for p in m.parameters()), torch.device("cpu"))
        r = A.shape[0]
        k = scale * ((alpha / r) if alpha else 1.0)
        # append, never replace: ART+ stacks three LoRAs on the same modules (v1-v8 silently kept only the last one)
        if not hasattr(m, "_fp16_lora"):
            m._fp16_lora = []
        m._fp16_lora.append((A.to(dev, torch.float16), B.to(dev, torch.float16), k))
        hit += 1
    return hit, miss


def remove_lora(model):
    for _, m in model.named_modules():
        if hasattr(m, "_fp16_lora"):
            del m._fp16_lora


def _patch_attention():
    # Qwen-Image attention only; other models (FLUX ports with older bundled diffusers) just get the Linear patch
    try:
        import diffusers.models.transformers.transformer_qwenimage as tq
    except ImportError:
        return
    if getattr(tq, "_fp16_orig_attn", None) is not None:
        return
    orig = tq.dispatch_attention_fn

    def attn_fp16(q, k, v, attn_mask=None, **kw):
        s = (v.float().abs().amax() / ATTN_LIMIT).clamp_(min=1.0)
        if attn_mask is not None and attn_mask.is_floating_point():
            attn_mask = attn_mask.to(torch.float16)
        o = orig(q.to(torch.float16), k.to(torch.float16), (v.float() / s).to(torch.float16), attn_mask=attn_mask, **kw)
        return o.float() * s

    tq._fp16_orig_attn = orig
    tq.dispatch_attention_fn = attn_fp16


def apply_fp16_mixed(model):
    """Patch a loaded QwenImageTransformer2DModel in place. Returns (linears patched, params moved to fp32)."""
    _patch_attention()
    n_lin = n_par = 0
    for _, m in model.named_modules():
        if "Linear" in type(m).__name__:
            if not hasattr(m, "_fp16_orig_forward"):
                m._fp16_orig_forward = m.forward
            m.forward = types.MethodType(_mixed_linear, m)
            n_lin += 1
        else:
            for _, p in m.named_parameters(recurse=False):
                if p.dtype == torch.float16:
                    p.data = p.data.float()
                    n_par += 1
    if not hasattr(model, "_fp16_orig_model_forward"):
        model._fp16_orig_model_forward = model.forward

        def fwd(*a, **k):
            o = model._fp16_orig_model_forward(*a, **k)
            if isinstance(o, tuple):
                if isinstance(o[0], (list, tuple)):          # ControlNet-style adapters return (list of block samples, ...)
                    return tuple([x.to(torch.float16) for x in e] if isinstance(e, (list, tuple)) else e for e in o)
                return (o[0].to(torch.float16),) + tuple(o[1:])
            if hasattr(o, "sample"):
                o.sample = o.sample.to(torch.float16)
            return o

        model.forward = fwd
    return n_lin, n_par
