"""Relight an RGBA layer against a background with IC-Light v1 "fbc" (SD1.5, Apache-2.0), keeping the layer's alpha.

Follows lllyasviel/IC-Light gradio_demo_bg.py: Realistic Vision 5.1 UNet with conv_in widened 4 -> 12 channels
(new channels zero), IC-Light fbc offsets added to the UNet weights, foreground and background VAE-encoded (mode *
scaling factor) and concatenated to the noisy latent at every step. Transparent foreground pixels are filled with
grey (127) before encoding, otherwise the result is darkened (ComfyUI-IC-Light note).

Use cases in the loop: after relocate() moves a layer, or after a story event changed the background (strategy c).
The output is RGB; we put back the layer's own alpha and optionally transfer the original's high-frequency detail
(like ComfyUI-IC-Light's DetailTransfer) so thin parts and texture stay identical while the light changes.

    rl = ICLightFBC(device="cuda", dtype=torch.float16)      # ~2.5 GB fp16 on a T4
    new_layer = rl.relight(layer_rgba, background_rgb, "campfire, warm firelight", steps=20)
"""
from __future__ import annotations

import numpy as np
import torch
from PIL import Image, ImageFilter

SD15 = "stablediffusionapi/realistic-vision-v51"
IC_REPO, IC_FILE = "lllyasviel/ic-light", "iclight_sd15_fbc.safetensors"


def _to_tensor(imgs, device, dtype):
    x = np.stack([np.asarray(i, np.float32) / 127.5 - 1.0 for i in imgs])
    return torch.from_numpy(x).permute(0, 3, 1, 2).to(device=device, dtype=dtype)


def _fg_on_grey(layer: Image.Image) -> Image.Image:
    x = np.asarray(layer.convert("RGBA"), np.float32)
    a = x[..., 3:] / 255
    return Image.fromarray((x[..., :3] * a + 127 * (1 - a)).astype(np.uint8))


def detail_transfer(new_rgb: Image.Image, orig_rgb: Image.Image, radius: float = 3.0, amount: float = 1.0):
    """new low frequencies (light) + original high frequencies (texture, thin parts)."""
    n, o = (np.asarray(i.convert("RGB"), np.float32) for i in (new_rgb, orig_rgb))
    lo = lambda a: np.asarray(Image.fromarray(a.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius)), np.float32)
    return Image.fromarray(np.clip(lo(n) + amount * (o - lo(o)), 0, 255).astype(np.uint8))


def restore_chroma(relit: Image.Image, original: Image.Image, keep: float = 0.7) -> Image.Image:
    """Keep the relit lightness (L) but pull the colour (Lab a, b) back towards the original layer's: IC-Light shifts hue
    (the fox turned red); keep=0 leaves the relit colour, keep=1 restores the original hue entirely. Alpha is the relit layer's."""
    from skimage import color

    r = np.asarray(relit.convert("RGB"), np.float32) / 255
    o = np.asarray(original.convert("RGB").resize(relit.size), np.float32) / 255
    lr, lo = color.rgb2lab(r), color.rgb2lab(o)
    lab = lr.copy()
    lab[..., 1:] = (1 - keep) * lr[..., 1:] + keep * lo[..., 1:]
    out = Image.fromarray((np.clip(color.lab2rgb(lab), 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(relit.convert("RGBA").getchannel("A"))
    return out


class ICLightFBC:
    def __init__(self, device="cuda", dtype=torch.float16, base=SD15):
        from diffusers import AutoencoderKL, DPMSolverMultistepScheduler, StableDiffusionPipeline, UNet2DConditionModel
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
        from transformers import CLIPTextModel, CLIPTokenizer
        self.device, self.dtype = torch.device(device), dtype
        tok = CLIPTokenizer.from_pretrained(base, subfolder="tokenizer")
        te = CLIPTextModel.from_pretrained(base, subfolder="text_encoder")
        vae = AutoencoderKL.from_pretrained(base, subfolder="vae")
        unet = UNet2DConditionModel.from_pretrained(base, subfolder="unet")
        with torch.no_grad():
            ci = unet.conv_in
            new = torch.nn.Conv2d(12, ci.out_channels, ci.kernel_size, ci.stride, ci.padding)
            new.weight.zero_(); new.weight[:, :4].copy_(ci.weight); new.bias = ci.bias
            unet.conv_in = new
            off = load_file(hf_hub_download(IC_REPO, IC_FILE))
            sd = unet.state_dict()
            unet.load_state_dict({k: sd[k] + off[k] for k in sd}, strict=True)
            del off, sd
        orig = unet.forward

        def fwd(sample, timestep, encoder_hidden_states, **kw):
            c = kw["cross_attention_kwargs"]["concat_conds"].to(sample)
            c = torch.cat([c] * (sample.shape[0] // c.shape[0]), 0)
            kw["cross_attention_kwargs"] = {}
            return orig(torch.cat([sample, c], 1), timestep, encoder_hidden_states, **kw)
        unet.forward = fwd
        # VAE kept in fp32: the demo uses bf16, which a T4 lacks; fp16 SD1.5 VAE can overflow
        te.to(self.device, dtype); unet.to(self.device, dtype); vae.to(self.device, torch.float32)
        sched = DPMSolverMultistepScheduler(num_train_timesteps=1000, beta_start=0.00085, beta_end=0.012,
                                            algorithm_type="sde-dpmsolver++", use_karras_sigmas=True, steps_offset=1)
        self.vae = vae
        self.pipe = StableDiffusionPipeline(vae=vae, text_encoder=te, tokenizer=tok, unet=unet, scheduler=sched,
                                            safety_checker=None, requires_safety_checker=False, feature_extractor=None)

    @torch.inference_mode()
    def relight(self, layer: Image.Image, background: Image.Image, prompt: str, steps: int = 20, cfg: float = 7.0,
                seed: int = 12345, size: int | None = None, a_prompt: str = "best quality",
                n_prompt: str = "lowres, bad anatomy, bad hands, cropped, worst quality",
                detail: float = 1.0, detail_radius: float = 3.0) -> Image.Image:
        W, H = layer.size
        w = h = size or max(W, H)
        w, h = (w // 64) * 64, (h // 64) * 64
        fg = _fg_on_grey(layer).resize((w, h), Image.LANCZOS)
        bg = background.convert("RGB").resize((w, h), Image.LANCZOS)
        x = _to_tensor([fg, bg], self.device, torch.float32)
        c = self.vae.encode(x).latent_dist.mode() * self.vae.config.scaling_factor
        c = torch.cat([c[i:i + 1] for i in range(2)], 1).to(self.dtype)
        lat = self.pipe(prompt=f"{prompt}, {a_prompt}", negative_prompt=n_prompt, width=w, height=h,
                        num_inference_steps=steps, guidance_scale=cfg, output_type="latent",
                        generator=torch.Generator(self.device).manual_seed(seed),
                        cross_attention_kwargs={"concat_conds": c}).images
        px = self.vae.decode(lat.float() / self.vae.config.scaling_factor).sample
        out = Image.fromarray(((px[0].permute(1, 2, 0).clamp(-1, 1) + 1) * 127.5).byte().cpu().numpy()).resize((W, H), Image.LANCZOS)
        if detail > 0:
            out = detail_transfer(out, layer.convert("RGB"), detail_radius, detail)
        out = out.convert("RGBA"); out.putalpha(layer.getchannel("A"))
        return out
