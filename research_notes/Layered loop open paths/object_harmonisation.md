# Object-layer harmonisation after place/move/resize: sources (status Nov 2026)

Methods to fix lighting, colour, shadows, contact and style on an RGBA layer after `relocate()`. Built from this: `prototype/layerproto/relight.py` (IC-Light fbc) and `shadow.py` (procedural shadow); measurements in [relight-ic-light.md](../../docs/models/relight-ic-light.md), [shadow-layers.md](../../docs/models/shadow-layers.md), [relocate-harmonise.md](../../docs/models/relocate-harmonise.md). Items marked [unverified] come from snippets or prior knowledge.

## 1. Relighting

- **IC-Light v1 fbc** (SD1.5, Apache-2.0) is the strongest background-conditioned relighter that runs on a T4. Models: `fc` (text + fg), `fcon`, `fbc` (text + fg + bg). Mechanism (`gradio_demo_bg.py`): base `stablediffusionapi/realistic-vision-v51`; `conv_in` widened 4 → 12 channels (new weights zeroed, old copied); the fbc offset added to the base UNet (`strict=True`); fg and bg VAE-encoded (`mode() × scaling`) into an 8-channel `c_concat`, concatenated to the noisy latent by a hooked UNet forward; DPM++ SDE Karras, 20 steps, CFG 7, 512×640, optional 1.5× highres pass at 0.5 denoise. The default matting model (BRIA RMBG-1.4) is non-commercial; BiRefNet is suggested. ComfyUI tips: fill the fg's transparent area with grey before encoding (else the background darkens); `DetailTransfer` restores high-frequency detail. [Repo](https://github.com/lllyasviel/IC-Light), [discussion #109](https://github.com/lllyasviel/IC-Light/discussions/109).
- **Usage recipe in diffusers** (follows the demo, glue untested): load the base, widen `conv_in`, add `iclight_sd15_fbc.safetensors` key by key, fg = RGBA over mid-grey 127 at full canvas, bg = the clean scene, sizes multiples of 64, `c_concat = cat([vae.encode(fg).mode(), vae.encode(bg).mode()]) × 0.18215`, wrap `unet.forward` to concatenate it (repeat for CFG), img2img at 0.4-0.7 strength, output alpha = the warped source alpha, then frequency-split paste-back (relit low-pass + original high-pass inside the eroded mask).
- **IC-Light v2 (FLUX):** never released weights ([discussion #98](https://github.com/lllyasviel/IC-Light/discussions/98): a Space, later 404 / startup error, and a fal.ai API; licence "non-commercial only"). `molidiss/iclight-v2` is unofficial.
- **LBM relighting** (Jasper AI, SDXL fine-tune, 1 step, CC BY-NC; the repo's licence badges conflict): relights a pasted composite in one step; also in libcom ([gojasper/LBM](https://github.com/gojasper/LBM)). SDXL fp16 about 7 GB.
- **DiT-class (too heavy for a few seconds on a T4):** `dx8152/Qwen-Image-Edit-2509-Relight` (Apache-2.0, used with the Lightning LoRA) and `-Fusion` (blend, fix perspective and lighting), `ostris/qwen_image_edit_inpainting`, flymy-ai InScene, QIE-2511 Object-Adder / Studio-DeLight / Light-Migration LoRAs; libcom's FLUX-Kontext blending/harmonisation LoRAs. SpotLight: training-free relighting of an inserted object controlled by a coarse user shadow (CC BY-NC-SA).

## 2. Compositing and harmonisation methods

| Method | Mechanism | Training-free | Code / licence | Base |
|---|---|---|---|---|
| Paint-by-Example | SD inpainting on a CLIP embedding of the exemplar | no | yes, OpenRAIL-M | SD1.x |
| AnyDoor | DINOv2 ID tokens + high-frequency detail map | no | yes, MIT | SD2.1 |
| MimicBrush | reference U-Net + imitative U-Net | no | yes, Apache-2.0 | two U-Nets |
| TF-ICON, PrimeComposer, FreeCompose, Diff-Harmonization | inversion / attention steering / frozen SD prior | yes | yes (Diff-Harmonization Apache-2.0) | SD |
| DiffHarmony | SD-inpainting with composite + mask conditions | no | announced | SD1.5-inpaint |
| libcom (BCMI) | toolbox: PCTNet / LBM harmonisation, shadows (GPSDiffusion), reflections, insertion, Kontext LoRAs | no | Apache-2.0 toolbox | mixed |
| Add-it | FLUX weighted extended attention + latent blending | yes | yes, NVIDIA + FLUX-dev NC | FLUX, >16 GB |
| Insert Anything | in-context editing, FLUX.1-Fill + LoRA | LoRA | yes, MIT + FLUX NC | 26 GB, 10 GB with int4 |
| PosBridge, LooseRoPE, Insert In Style | positional-embedding / RoPE transplant, FLUX LoRAs | mostly | unclear | FLUX |
| ObjectStitch, ObjectDrop, Thinking outside the BBox | trained, include shadows and reflections | no | no public code found | |

No "OmniHarmony" paper exists, and no Qwen-Image-2.1-specific insertion or harmonisation method was found. None of these compares reference-only attention, KV injection, IP-Adapter, latent pinning and paste-back head to head; move/resize editors report their own metrics (GeoDiffuser: CLIP, warp error, mean distance; RegionDrag: LPIPS, mean distance; a 2025 geometric-editing paper: DINO subject and CLIP background consistency). The mechanisms with the best evidence are source-path KV/self-attention sharing (RegionDrag, DragonDiffusion family, Add-it) and detail transfer (AnyDoor, IC-Light DetailTransfer). Magic Fixup (Adobe, trained on video frames, 7.7 GB, research licence) turns a coarse move/resize into a photoreal output; DesignEdit (MIT) does move/resize/remove with SDXL layered latents; DreamLayer's IRH ablation shows a chair "floats" with no shadow without harmonisation.

## 3. Shadows and reflections

Released: SGDiffusion (DESOBAv2, 21,575 images, CVPR'24), GPSDiffusion (CVPR'25, geometry prior, SD1.5 and SDXL versions; the README warns results are unstable, generate several), BCMI's reflection model (DEROBA, [2604.02168](https://arxiv.org/html/2604.02168v1)), all in libcom. All output a composite with the shadow, not a layer; a darkening matte can be taken by differencing the output against the input. Shadow-as-layer: LayerDecomp (Adobe/UCSC, CVPR'25, effects kept in the transparent layer, no code found), Generative Omnimatte (video), a USPTO patent. **EasyOmnimatte (CVPR'26) synthesises shadow mattes from the foreground alpha by vertical compression, shear, semi-transparency and blur: the recipe `shadow.py` implements.**

## 4. Pipeline estimated from the sources (3-6 s at 512 px, not benchmarked)

`relocate()` warp with SDXL bg2ble, eroded-interior pinning and source-KV sharing → relight with IC-Light fbc (0.4-0.6 strength) or LBM in 1 step → frequency-split paste-back with the original alpha → procedural shadow layer, optionally refined by a GPSDiffusion luminance-ratio matte → optional SDXL inpaint over the contact zone. The FLUX/Qwen paths (libcom Kontext LoRA, Qwen-Edit Fusion/Relight, Add-it, Insert Anything) are an offline polish step.
