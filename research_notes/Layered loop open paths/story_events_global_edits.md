# Story events: global edits across a layered RGBA scene, sources (Nov 2026)

Weather, time of day, fire, season and lighting applied consistently to background and object layers; target Kaggle 2× T4 (fp16). Our measured strategies and results: [docs/concepts/editing.md §3-5](../../docs/concepts/editing.md). [unverified] marks anything not confirmed on a primary page.

## 1. Consistent multi-image and video editing

- **StyleAligned** (CVPR 2024, Apache-2.0, archived 2025-03-03, [repo](https://github.com/google/style-aligned)): every image in a batch shares attention with the first, AdaIN on queries and keys, no optimisation; SDXL, SDXL + ControlNet-Depth notebooks (PyTorch 2.1, Diffusers 0.16); "from an input image" is still a TODO. It favours diverse structure with consistent style, so pair it with img2img or ControlNet-Depth to keep layer geometry. The drop-in candidate for "same event on every layer".
- **Edicho** (ICCV 2025, [2412.21079](https://arxiv.org/html/2412.21079v3)): training-free consistent editing of several real images through correspondence-guided attention and CFG, on top of an inpainting editor (BrushNet). ConsiStory shares activations for consistent *generation*, not editing.
- **TokenFlow** (ICLR 2024, MIT) and **Rerender-A-Video** (SD1.5 + ControlNet, "24GB VRAM is required") are video-frame propagators: they suit "same layer before and after", not different layers. **DreamLayer's Layer-Shared Self-Attention** (latents of all layers concatenated along the sequence) is the mechanism a joint layer edit would need.

## 2. Relighting and weather

- **IC-Light v1** (Apache-2.0, SD1.5; `fc`, `fbc`, `fcon`) and **LBM relighting** (CC BY-NC 4.0, one step, `get_model("jasperai/LBM_relighting")`, `evaluate(model, source_image, num_sampling_steps=1)` on a single composite; ICCV 2025 highlight, a latent Brownian bridge conditioned on a light map; the card's example uses bf16, a T4 needs fp16, untested) are the T4-viable options. Both output RGB, so alpha is kept or re-estimated. IC-Light v2 (FLUX) has its own licence and no weights. The bundled BRIA RMBG 1.4 is non-commercial; BiRefNet is suggested. Details: [object_harmonisation.md](object_harmonisation.md).
- **WeatherEdit** (AAAI-26, [code](https://github.com/Jumponthemoon/WeatherEdit)): a 3D Gaussian-splatting scene pipeline built on img2img-turbo and OmniRe; its 2D adapter edits the background for snow, rain and fog from text + segmentation, and might be extractable as a one-step SD-Turbo model [unverified]. WeatherWeaver (NVIDIA, video, no code), SceneCrafter (Waymo, no code), LightIt (shading-conditioned ControlNet, no code), Neural Gaffer (object relighting under an environment map, Zero123-based, 8-GPU training) and DiLightNet (radiance-hint ControlNet on SD2.1) are not T4-practical.

## 3. Strategy evidence

No source compares the strategies head to head. The architecture evidence (WeatherEdit separates background editing from the particle layer; LASAGNA, [2601.15507](https://arxiv.org/abs/2601.15507v1), and DreamLayer generate layers with their shadows and effects) favours (c) edit the background and relight the foregrounds, plus (d) separate effect layers, with (a) re-split the edited composite (Qwen-Image-Layered or Stable-Layers) as the fallback for geometry-changing events. LayerDiffuse supports foreground- or background-conditioned generation (semi-transparent fire in its examples); no source shows LayerDiffuse rain, snow, fog or smoke overlays. Game engines do rain and wetness with shaders and particles (Unity Shader Graph "Production Ready Weather" sample), which is why our effect layers are procedural.

## 4. Layered papers and global edits

No layered paper offers event-driven or global relight/weather edits across layers. Joint-generation papers (DreamLayer, LayerFusion [training-free, spatial edits], PSDiffusion, OmniPSD, LayerCraft, ART, CLD, Stable-Layers; abstracts and snippets only) give cross-layer attention that could be reused by regenerating with a changed global prompt. Only the anime Workflow-Aware Structured Layer Decomposition ([2603.14925](https://arxiv.org/html/2603.14925), line art / base colour / shading) targets relighting.

## 5. Practice evidence

No AIIDE / FDG / CHI PLAY paper on generative day/night or weather changes was found. Indie devlogs lock the layout (sketch or ControlNet) and pre-generate a variant per state ([itch.io](https://itch.io/blog/1145381/solved-how-to-keep-ai-backgrounds-geometrically-consistent-day-vs-night)); VinA (Ren'Py + Stable Diffusion WebUI) has no weather features; an ACM talk cites about 10 s per image as the barrier to live changes.
