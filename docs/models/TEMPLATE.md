# Model factsheet template

> **Role: template for every file in this folder.** Copy the headings, keep their order. Verdicts ("best", "recommended") are the user's; a factsheet reports measurements and shows images. Qwen-Image-2.1 ([qwen-image-2.1.md](qwen-image-2.1.md)) is the reference file.

## The shared test (so every model is judged on the same input)

- **Image:** [`prototype/test_scene/fox_cottage.png`](../../prototype/test_scene/fox_cottage.png) (512 px, seed 13), caption and five boxes in [`fox_cottage.json`](../../prototype/test_scene/fox_cottage.json): village houses, cottage, stone gate arch, big tree, red fox.
- **Path A, best case:** the settings that gave the best result so far, up to 8 minutes of compute per image.
- **Path B, live-demo budget:** the same input at the cheapest settings, aiming for **about 30 s of compute per image**. Compute means the generation call only (what a frontend request would wait for), **not** the model load. If a model cannot reach 30 s, run it at its cheapest settings anyway and report the real time.
- **Always report:** hardware, settings, compute seconds, load seconds, peak GB, layer count, a strip image (input | layers | recomposite) and the recomposite difference where we have it.

## Headings

1. **What it does.** Two or three lines, then a one-line type tag: input → output (for example "image + boxes → layers").
2. **Licence & weights.** Licence, repository, size, anything gated, and whether the weights are already attached to a Kaggle dataset (for pre-downloaded live use).
3. **How we run it.** Numbered steps for the happy path, the module in `prototype/layerproto/backends/` (or the generator script while it is not extracted yet) and the `/decompose` method name.
4. **Fox & cottage benchmark.**
   - **A. Best case** (table + strip image).
   - **B. Live-demo budget, about 30 s** (table + strip image).
   - One sentence on what differs between A and B.
5. **Further investigations.** Everything else we measured on this model (other scenes, 1024 px probes, halo fix, drift, story events), each with its own small table or image.
6. **Special features.** A checklist table, then one short subsection per feature that is marked supported or tested, each with an **image example on the fox & cottage scene** and the measured time. Features that do not apply say "n/a" with the reason; features we have not tried say "not tried".

   | Feature | Status | Evidence |
   |---|---|---|
   | Split an image into layers | | |
   | Move / resize a layer | | |
   | Harmonise after a move (light, contact shadow) | | |
   | Story composite (the scene changes: night, rain ...) | | |
   | Spatial edit (change one region or object) | | |
   | Image to image (edit the whole picture) | | |
   | Add / remove / modify a layer | | |
   | Relight a layer | | |
   | Effects as layers (fog, glow, snow) | | |
   | Amodal completion (hidden parts of an object) | | |

   Status values: **supported** (shown in an image below), **partial** (works with caveats stated), **not tried**, **n/a**.
7. **Best features / Weak spots.** What the images above show, in a few bullets each.
8. **Status / Next attempts / Sources.** One line of status, the open items, the links.

## Rules for adding results

- **Name every model in a combination** and add the chain to [provenance.md](provenance.md). Many results chain models (an edit by Qwen-Image-2.1, then a split by Stable-Layers; objects from one model on a background from another). Each image caption and table row says which model produced which part, so a good or bad result can be traced to one model. A combined run of the best model per purpose is planned (docs/todo.md).

- Every claim in section 6 links to an image under `docs/img/` and to the results folder it came from.
- Put the generated comparison row in `prototype/kaggle/benchmarks.csv` (the README table is built from it by `prototype/tools/build_benchmarks.py`).
- After a change run `prototype/tools/check_doc_links.py` before pushing.
