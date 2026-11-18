# Spatial edit and re-harmonise: mechanics from LayerFusion, DreamLayer, PSDiffusion

Sources read 2026-11-09 through arXiv HTML pages with a summarising fetch tool; numbers are as reported by it, check the PDF before relying on them. Built from this: `LayerDiffuseChain.relocate()` (v5: Euler, mask extraction, interior pinning, paste-back; about 4 s per edit on a T4): [concepts/editing.md §1](../../docs/concepts/editing.md), [relocate-harmonise.md](../../docs/models/relocate-harmonise.md). None of the three papers has public code.

## What each paper does

**LayerFusion** ([2412.04460](https://arxiv.org/html/2412.04460)) is training-free but needs more than LayerDiffuse alone: the FG (RGBA) branch uses LayerDiffuse SDXL, the BG and blend branches plain SDXL (RealVisXL_V4.0), all denoised together in one batch.
- Structure prior from the last self-attention layer of the FG branch (`up.1.attns.2.block.1`): per-token sparsity s_i = 1/Σ_j m_ij², inverted s' = 1 − normalize(s). Content prior c = the cross-attention column of the `<EOS>` token of the FG prompt, averaged over heads.
- mask_soft = normalize(s'·c); mask_hard = sigmoid(10·(mask_soft − 0.5)); masks taken at t = 0.8T.
- Blending: `a'_Blended = a_FG·mask_soft + a_Blended·(1−mask_soft)`, `a'_FG = a'_Blended·mask_hard + a_FG·(1−mask_hard)`, plus attention sharing between blend and BG states (self- and cross-attention). Which layers and timestep range it covers is unclear (read Alg. 3).
- Spatial editing: only claimed "in a straight-forward manner"; **no move / resize algorithm**.

**DreamLayer** ([2503.12838](https://arxiv.org/html/2503.12838)) is trained: SD1.5 with Custom-Diffusion K/V fine-tuning (lr 2e-6, 60k steps, 2×A100 for about 4 days); CACA at resolution 16 and LSSA in the up-blocks (all layer latents concatenated into a joint K/V); image-to-layer decomposition is training-free (DDIM inversion plus mask attention).
- **Information Retained Harmonization (IRH), the part we borrowed:** 50-step DDIM, layers generated separately down to T_H = 600, then alpha-composited at the latent level (Eq. 12): `z_m = z_bg·Π(1−α_i) + Σ_i z_i·α_i·Π_{f in front}(1−α_f)`; denoising continues from the composite, which is where shadows and contact appear (without IRH objects "appear to float").
- Move / flip / resize (Eq. 13): apply the operation to the FG latents and alphas before the Eq. 12 fusion, then re-denoise; the floor shadow follows the chair.

**PSDiffusion** ([2505.11468](https://arxiv.org/html/2505.11468)): partial joint self-attention Q = W_Q z_i, K = W_K[K_GL, K_L], V = W_V[V_GL, V_L] with K_GL = K_G·Mask_i^g (the mask is the global cross-attention map, filtered, blurred, binarised; thresholds not given), in all self-attention layers; SDXL LoRA rank 256, about 60 A800-hours, 30K-sample Inter-Layer dataset. Without the trained projections the mechanism is only a heuristic.

## Takeaway and the recipe we implemented

None gives a ready-made training-free spatial-edit algorithm for SDXL LayerDiffuse. The closest is DreamLayer's IRH, which maps onto our `bgble2fg` / `bg2ble` modes plus SDEdit-style partial re-noising:

1. Warp the layer's RGB and alpha from the old box to the new one in pixel space (SDXL latents are /8) and paste over the background → naive composite and alpha A1.
2. If the background still contains the old object, inpaint the old box first (normally skip: use a clean `bg`).
3. VAE-encode, re-noise to t_s = s·T (strength s 0.4-0.55; DreamLayer's T_H/T = 0.6 is only a start, and for trained SD1.5).
4. Denoise with the `bg2ble` blend pipeline from t_s to 0 conditioned on the background; **pin the object's interior** in the first k % of the remaining steps (`z = M_core·noised(z0_fg) + (1−M_core)·z`, M_core = eroded A1) so the ring and the outside stay free for shadows and contact. Optional LayerFusion-style soft attention mask from a reference pass (doubles the cost).
5. Re-extract the foreground (`bgble2fg`; we found mask extraction better) and output the new blend plus the new RGBA layer.

Open points: low strength keeps the object but gives weak or stale shadows, high strength fixes lighting but drifts identity; occlusion with other objects needs a z-order composite per Eq. 12 and, for multi-object scenes, trained joint attention; resizing up softens the object, so consider regenerating it at the new size.
