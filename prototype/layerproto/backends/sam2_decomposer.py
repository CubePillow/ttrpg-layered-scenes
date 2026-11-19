"""Image -> layers with Grounding DINO + SAM2 + LaMa: segment BY NOUN, fill the background (7 s + fill on a T4).

    dec = Sam2Decomposer(device="cuda")   # needs: pip install git+https://github.com/facebookresearch/sam2 simple-lama-inpainting
    layers = dec(image, DecomposeParams(names=["cottage", "red fox"]))   # background first, then objects in the given order
    # or boxes: DecomposeParams(boxes=[[x0, y0, x1, y1], ...], names=[...]) skips Grounding DINO

Pass `dec` as `decomposer=` to layerproto.remote_server.build_app to serve it on /decompose.
Measured on fox & cottage: docs/models/sam2-lama.md.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .decomposer import DecomposeParams


class Sam2Decomposer:
    def __init__(self, device: str = "cuda", sam_id: str = "facebook/sam2-hiera-small",
                 dino_id: str = "IDEA-Research/grounding-dino-tiny"):
        import torch
        from sam2.build_sam import build_sam2_hf
        from sam2.sam2_image_predictor import SAM2ImagePredictor
        from simple_lama_inpainting import SimpleLama
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.torch, self.device = torch, device
        self.pred = SAM2ImagePredictor(build_sam2_hf(sam_id, device=device))
        self.proc = AutoProcessor.from_pretrained(dino_id)
        self.dino = AutoModelForZeroShotObjectDetection.from_pretrained(dino_id).to(device)
        self.lama = SimpleLama()
        self._inpaint = None                                # SDXL-inpaint, loaded on the first amodal request

    amodal_neutral = False      # True: inpaint on the object over neutral grey. Tested 2026-11-10: removes the green patches but the fill comes out grey

    def _fill_hidden(self, base: Image.Image, hidden: np.ndarray, prompt: str, seed: int = 5) -> Image.Image:
        """SDXL-inpaint `base` inside `hidden` (bool mask); returns an RGB image of base's size."""
        if self._inpaint is None:
            from diffusers import AutoencoderKL, StableDiffusionXLInpaintPipeline
            vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=self.torch.float16)
            self._inpaint = StableDiffusionXLInpaintPipeline.from_pretrained(
                "diffusers/stable-diffusion-xl-1.0-inpainting-0.1", vae=vae, torch_dtype=self.torch.float16, variant="fp16").to(self.device)
        S = 1024
        mask = Image.fromarray((hidden * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.5))
        out = self._inpaint(prompt=f"a complete {prompt}, the same material and colours continuing, storybook illustration",
                            negative_prompt="grass, hedge, leaves, sky, tree, background, text, watermark, extra objects",
                            image=base.resize((S, S), Image.LANCZOS), mask_image=mask.resize((S, S)), num_inference_steps=30,
                            strength=0.99, guidance_scale=7.0, generator=self.torch.Generator(self.device).manual_seed(seed)).images[0]
        return out.resize(base.size, Image.LANCZOS).convert("RGB")

    def _box_for(self, im: Image.Image, name: str):
        H, W = im.size[1], im.size[0]
        inp = self.proc(images=im, text=name.lower() + ".", return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            out = self.dino(**inp)
        r = self.proc.post_process_grounded_object_detection(out, inp.input_ids, threshold=0.3, text_threshold=0.25,
                                                             target_sizes=[(H, W)])[0]
        if len(r["boxes"]) == 0:
            return None
        return [float(x) for x in r["boxes"][int(r["scores"].argmax())].tolist()]

    def _mask(self, arr, box):
        self.pred.set_image(arr)
        m, _s, _ = self.pred.predict(box=np.array(box, dtype=np.float32), multimask_output=False)
        return m[0].astype(bool)

    def __call__(self, image: Image.Image, p: DecomposeParams) -> list[Image.Image]:
        im = image.convert("RGB")
        arr = np.asarray(im)
        H, W = arr.shape[:2]
        boxes = list(p.boxes) or [self._box_for(im, n) for n in p.names]
        names = list(p.names) + [f"object {i + 1}" for i in range(len(p.names), len(boxes))]
        masks = [(n, self._mask(arr, b)) for n, b in zip(names, boxes) if b is not None]
        mboxes = [b for b in boxes if b is not None]        # aligned with masks
        if not masks:
            raise ValueError("no object found: pass names (nouns) or boxes")
        taken = np.zeros((H, W), bool)
        owned = []
        for name, m in reversed(masks):                     # front layers own overlapping pixels
            mm = m & ~taken
            taken |= mm
            owned.append((name, mm))
        owned.reverse()
        hole = Image.fromarray((taken * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
        layers = [self.lama(im, hole).resize(im.size).convert("RGBA")]
        for i, (_name, mm) in enumerate(owned):
            a = Image.fromarray((mm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
            L = im.convert("RGBA")
            L.putalpha(a)
            if getattr(p, "amodal", False) and i < len(owned) - 1:   # the front-most object has nothing hiding it
                L = self._complete(layers[0], L, masks, i, mboxes, W, H)
            layers.append(L)
        return layers

    def _complete(self, bg: Image.Image, L: Image.Image, masks, i: int, boxes, W: int, H: int) -> Image.Image:
        """Fill the part of object i's box that objects in front of it cover (box minus its own mask), keep its own pixels."""
        front = np.zeros((H, W), bool)
        for _n, m in masks[i + 1:]:
            front |= m
        box = np.zeros((H, W), bool)
        x0, y0, x1, y1 = [int(round(v)) for v in boxes[i]]
        box[max(0, y0):y1, max(0, x0):x1] = True
        hidden = box & front & ~masks[i][1]
        if hidden.mean() < 0.002:
            return L
        base = Image.new("RGBA", (W, H), (128, 128, 128, 255)) if self.amodal_neutral else bg.convert("RGBA")
        base.alpha_composite(L)
        filled = self._fill_hidden(base.convert("RGB"), hidden, masks[i][0])
        h = np.asarray(Image.fromarray((hidden * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 255
        own = np.asarray(L, np.float32)
        rgb = np.where(h[..., None] > 0.5, np.asarray(filled, np.float32), own[..., :3])
        alpha = np.maximum(own[..., 3], h * 255)
        return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")
