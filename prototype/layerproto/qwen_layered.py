"""Qwen-Image-Layered decomposition: one finished image -> N RGBA layers that composite back to it.

Shared by the local dry run (tools/dryrun_qwen_layered.py, tiny random models, CPU) and the Kaggle test notebook
(real 8-bit text encoder + 4-bit GGUF transformer on a T4), so the call path is verified before any big download.

Two stages so a 16 GB T4 is enough:
    1. text encoder encodes the caption (prompt embeddings), then is unloaded
    2. transformer decomposes the image using those embeddings
"""
from __future__ import annotations

import gc
import time
import types

import numpy as np
import torch
from PIL import Image

REPO = "Qwen/Qwen-Image-Layered"


def make_pipeline(text_encoder, vae, repo: str = REPO):
    """Pipeline without a transformer yet (it is loaded after the text encoder is gone)."""
    from diffusers import FlowMatchEulerDiscreteScheduler, QwenImageLayeredPipeline
    from transformers import Qwen2Tokenizer, Qwen2VLProcessor

    return QwenImageLayeredPipeline(
        scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(repo, subfolder="scheduler"),
        vae=vae, text_encoder=text_encoder,
        tokenizer=Qwen2Tokenizer.from_pretrained(repo, subfolder="tokenizer"),
        processor=Qwen2VLProcessor.from_pretrained(repo, subfolder="processor"),
        transformer=None)


def encode(pipe, caption: str, device, max_len: int = 512):
    """Prompt + negative (' ') embeddings. encode_prompt returns mask=None when the mask is all ones, but
    __call__ insists on a mask whenever embeddings are passed in, so all-ones masks are rebuilt here."""
    with torch.no_grad():
        pe, pm = pipe.encode_prompt(prompt=caption, device=device, num_images_per_prompt=1, max_sequence_length=max_len)
        ne, nm = pipe.encode_prompt(prompt=" ", device=device, num_images_per_prompt=1, max_sequence_length=max_len)

    def ones(e):
        return torch.ones(e.shape[:2], dtype=torch.long, device=e.device)

    return pe, (pm if pm is not None else ones(pe)), ne, (nm if nm is not None else ones(ne))


def cached_encode(pipe, caption: str, device, cache_dir: str, max_len: int = 512):
    """encode() with a disk cache keyed by caption: a cache hit means the 15 GB text encoder never has to be loaded
    (Kaggle: ~70 s load + RAM). Typical loop use: one fixed caption ("" or the scene prompt) per scene."""
    import hashlib
    import os
    os.makedirs(cache_dir, exist_ok=True)
    f = os.path.join(cache_dir, hashlib.sha1(f"{caption}|{max_len}".encode()).hexdigest()[:16] + ".pt")
    if os.path.exists(f):
        return tuple(t.to(device) for t in torch.load(f, map_location="cpu"))
    out = encode(pipe, caption, device, max_len)
    torch.save(tuple(t.detach().cpu() for t in out), f)
    return out


class HeunVelocity:
    """Turn the pipeline's Euler step into Heun's method (what Stable-Layers' decompose.py uses) without touching the
    pipeline: the transformer wrapper returns v_heun = (v(x, s) + v(x + dt*v(x, s), s_next)) / 2, so the pipeline's
    own Euler update x + dt*v_heun is exactly a Heun step. Final step (s_next = 0) stays Euler, as in Stable-Layers.
    Only the generated tokens are advanced for the midpoint; the trailing condition-image tokens stay fixed.
    Cost: 2 transformer calls per step (1 on the last step)."""

    def __init__(self, transformer, scheduler, layers: int):
        self.t, self.sched, self.frac = transformer, scheduler, (layers + 1) / (layers + 2)
        self.orig = transformer.forward

    def __enter__(self):
        self.t.forward = self.forward
        return self

    def __exit__(self, *a):
        self.t.forward = self.orig

    def _next_sigma(self, s):
        sig = self.sched.sigmas.to(torch.float32).cpu()
        i = int(torch.argmin((sig - s).abs()))
        return float(sig[i + 1]) if i + 1 < len(sig) else 0.0

    def forward(self, hidden_states, *a, timestep=None, **kw):
        out1 = self.orig(hidden_states, *a, timestep=timestep, **kw)
        v1 = out1[0] if isinstance(out1, tuple) else out1.sample
        s = float(timestep.flatten()[0])                 # pipeline passes sigma (timestep / 1000)
        s_next = self._next_sigma(s)
        if s_next <= 0:
            return out1
        n = int(round(hidden_states.shape[1] * self.frac))
        x_mid = hidden_states.clone()
        x_mid[:, :n] = hidden_states[:, :n] + (s_next - s) * v1[:, :n].to(hidden_states.dtype)
        out2 = self.orig(x_mid, *a, timestep=torch.full_like(timestep, s_next), **kw)
        v2 = out2[0] if isinstance(out2, tuple) else out2.sample
        v = 0.5 * (v1 + v2)
        if isinstance(out1, tuple):
            return (v,) + tuple(out1[1:])
        out1.sample = v
        return out1


def unload_text_encoder(pipe, dtype):
    """Free the text encoder. The pipeline still reads text_encoder.dtype later, so leave a stand-in;
    object.__setattr__ bypasses diffusers' component registration (which rejects non-modules)."""
    te = pipe.text_encoder
    object.__setattr__(pipe, "text_encoder", types.SimpleNamespace(dtype=dtype))
    del te
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def fix_gguf_non_linear(model, dtype) -> int:
    """diffusers' GGUF loader only swaps nn.Linear for dequantizing GGUFLinear layers. Any other module keeps its raw
    packed bytes, e.g. the layered model's addition_t_embedding (nn.Embedding(2, 3072)) returns 6144 bytes instead of
    3072 fp16 values -> 'size of tensor a (3072) must match ... (6144)'. Dequantize those parameters once after loading."""
    from diffusers.quantizers.gguf.utils import GGUFLinear, GGUFParameter, dequantize_gguf_tensor

    fixed = 0
    for mod in model.modules():
        for name, p in list(mod.named_parameters(recurse=False)):
            if isinstance(mod, GGUFLinear) and name == "weight":
                continue  # GGUFLinear dequantizes its own weight; its bias is not, so it is handled here too
            if isinstance(p, GGUFParameter):
                setattr(mod, name, torch.nn.Parameter(dequantize_gguf_tensor(p).to(dtype), requires_grad=False))
                fixed += 1
    return fixed


def decompose(pipe, transformer, image: Image.Image, caption: str, embeds, steps: int = 50, layers: int = 4,
              resolution: int = 640, seed: int = 777, true_cfg: float = 4.0, on_step=None,
              offload: bool = True, sampler: str = "euler"):
    """Run the decomposition. Returns (list of RGBA layers, stats). sampler="heun" doubles the transformer calls
    (Stable-Layers recommends Heun; its decompose.py uses linear sigmas, here the pipeline's schedule is kept)."""
    pipe.register_modules(transformer=transformer)
    image = image.convert("RGBA")  # the layered VAE has 4 input channels (as in the model card example)
    pe, pm, ne, nm = embeds
    gen_device = "cuda" if pe.is_cuda else "cpu"
    times, grabbed = [], {}

    class _Stop(Exception):
        pass

    def cb(p, i, t, kw):
        times.append(time.time())
        if on_step:
            on_step(i)
        if i == len(p.scheduler.timesteps) - 1:   # last step (Heun schedulers have ~2x steps timesteps)
            # Take the final latents and stop before the pipeline's own decode: it would run the VAE while the
            # 12.7 GB transformer is still on the GPU (OOM on a 15 GB T4), and output_type="latent" is broken in
            # diffusers 0.37 (that branch returns an unassigned `images` variable).
            grabbed["latents"] = kw["latents"]
            raise _Stop
        return kw

    # the pipeline only accepts 640 / 1024; for other sizes (e.g. 512, 384) swap in our target area
    import diffusers.pipelines.qwenimage.pipeline_qwenimage_layered as _pl
    _orig_cd = _pl.calculate_dimensions
    if resolution not in (640, 1024):
        _pl.calculate_dimensions = lambda area, ratio: _orig_cd(resolution * resolution, ratio)
    t0 = time.time()
    import contextlib
    heun = HeunVelocity(transformer, pipe.scheduler, layers) if sampler == "heun" else contextlib.nullcontext()
    try:
        with torch.no_grad(), heun:
            pipe(image=image, prompt=caption, prompt_embeds=pe, prompt_embeds_mask=pm,
                 negative_prompt_embeds=ne, negative_prompt_embeds_mask=nm, true_cfg_scale=true_cfg,
                 layers=layers, resolution=resolution if resolution in (640, 1024) else 640, num_inference_steps=steps, cfg_normalize=True,
                 generator=torch.Generator(gen_device).manual_seed(seed), callback_on_step_end=cb,
                 callback_on_step_end_tensor_inputs=["latents"])
    except _Stop:
        pass
    finally:
        _pl.calculate_dimensions = _orig_cd
    stats = {"denoise_s": round(time.time() - t0, 1)}
    if len(times) > 1:
        stats["s_per_step"] = round((times[-1] - times[0]) / (len(times) - 1), 2)

    # free the GPU before decoding: move the weights to CPU RAM (works even while the caller still holds `transformer`).
    # offload=False keeps it on the GPU(s) (enough room when it is split over two T4s or at small resolutions)
    if offload:
        transformer.to("cpu")
    pipe.register_modules(transformer=None)
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    t1 = time.time()
    imgs = decode_latents(pipe, grabbed["latents"], image.size, layers, resolution)
    stats["decode_s"] = round(time.time() - t1, 1)
    return imgs, stats


def decode_latents(pipe, latents, image_size, layers: int, resolution: int):
    """Same maths as the end of QwenImageLayeredPipeline.__call__, but decoding one layer at a time."""
    from diffusers.pipelines.qwenimage.pipeline_qwenimage_layered import calculate_dimensions

    w, h = calculate_dimensions(resolution * resolution, image_size[0] / image_size[1])
    m = pipe.vae_scale_factor * 2
    w, h = w // m * m, h // m * m
    vae = pipe.vae
    lat = pipe._unpack_latents(latents, h, w, layers, pipe.vae_scale_factor).to(vae.dtype)
    mean = torch.tensor(vae.config.latents_mean).view(1, vae.config.z_dim, 1, 1, 1).to(lat.device, lat.dtype)
    inv_std = 1.0 / torch.tensor(vae.config.latents_std).view(1, vae.config.z_dim, 1, 1, 1).to(lat.device, lat.dtype)
    lat = lat / inv_std + mean
    b, c, f, hh, ww = lat.shape
    lat = lat[:, :, 1:]  # first frame is the input image, not an output layer
    lat = lat.permute(0, 2, 1, 3, 4).reshape(-1, c, 1, hh, ww)
    out = []
    with torch.no_grad():
        for k in range(lat.shape[0]):
            img = vae.decode(lat[k:k + 1], return_dict=False)[0].squeeze(2)
            out.extend(pipe.image_processor.postprocess(img, output_type="pil"))
            del img
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    return [im.convert("RGBA") for im in out]


def recompose(layers, size=None):
    """Stack the layers bottom to top; returns (image, per-layer alpha stats)."""
    canvas, info = None, []
    for L in layers:
        a = np.array(L)[..., 3]
        info.append({"size": L.size, "transparent_pct": round(100 * float((a < 10).mean()), 1),
                     "opaque_pct": round(100 * float((a > 245).mean()), 1),
                     "has_nan_black": bool((np.array(L)[..., :3].max(-1) == 0).mean() > 0.95)})
        canvas = L if canvas is None else Image.alpha_composite(canvas, L.resize(canvas.size))
    if canvas is not None and size:
        canvas = canvas.resize(size)
    return canvas, info


def strip(images, w: int = 256) -> Image.Image:
    """Side-by-side preview; green shows transparency."""
    out = Image.new("RGBA", (w * len(images), w), (40, 160, 60, 255))
    for i, im in enumerate(images):
        tile = Image.new("RGBA", (w, w), (40, 160, 60, 255))
        tile.alpha_composite(im.convert("RGBA").resize((w, w)))
        out.paste(tile, (i * w, 0))
    return out
