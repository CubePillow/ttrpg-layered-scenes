"""Layer prototype UI (localhost, single user): a thin client. All models run on one Kaggle GPU session started from here.

    python prototype/app.py            (or prototype/run_prototype.bat)
Then open http://127.0.0.1:7870 (change the port with LAYERPROTO_PORT).

Flow: Start the Kaggle session (SDXL-Turbo + Qwen-Image-2.1) -> make the picture (text, or a sketch / uploaded picture as image to image,
one or several versions) -> split it into layers (Qwen-Image-2.1, or another splitter) -> work on the layers in the canvas editor
(select with rectangle / lasso, move, resize, rotate, reorder; Qwen-Image-2.1 edits of one layer). Nothing is computed on this machine.
"""
from __future__ import annotations

import glob
import os
import sys
import traceback
import warnings
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")  # printed by Gradio on every click

import gradio as gr  # noqa: E402
from PIL import Image  # noqa: E402

from layerproto import connection, editor_api, kaggle_launch  # noqa: E402
from layerproto.backends.decomposer import DecomposeParams  # noqa: E402
from layerproto.config import load_settings  # noqa: E402
from layerproto.engine import Engine  # noqa: E402
from layerproto.scene import Scene, new_scene_id  # noqa: E402
from layerproto.serve.profiles import PROFILES  # noqa: E402

S = load_settings()
ENGINE = Engine(S)

# label -> (server profile, method, connection role). Qwen-Image-2.1 runs in the main session; the others need a session of their own.
SPLITTERS = {
    "Qwen-Image-2.1 (extract the objects you name)": ("studio", "qwen21-extract", "split"),
    "Qwen-Image-Layered (all layers in one pass)": ("qwen-layered", "qwen-layered", "alt"),
    "Stable-Layers (Qwen-Image-Layered + LoRA)": ("qwen-layered", "stable-layers", "alt"),
    "Qwen-Image-Lightning (fewer steps)": ("qwen-layered", "qwen-lightning", "alt"),
    "SAM2 + Grounding DINO + LaMa (masks by name)": ("sam2", "sam2-lama", "alt"),
    "RevealLayer (boxes, filled backgrounds)": ("reveallayer", "reveallayer", "alt"),
    "CLD (boxes)": ("cld", "cld", "alt"),
}
DEFAULT_SPLITTER = next(iter(SPLITTERS))
NEEDS = {                      # which inputs a method uses: names, boxes, layers, amodal, sampler
    "qwen21-extract": {"names"}, "qwen-layered": {"layers", "sampler"}, "stable-layers": {"layers", "sampler"},
    "qwen-lightning": {"layers", "sampler"}, "sam2-lama": {"names", "boxes", "amodal"}, "reveallayer": {"names", "boxes"}, "cld": {"names", "boxes"},
}
EDITOR_JS = "() => { const f = document.getElementById('layer-editor'); if (f && f.contentWindow) f.contentWindow.postMessage({type: 'reload'}, '*'); }"
# before a model call or a version pick, make the editor save its pending changes (the server reads the stored layer)
FLUSH_JS = ("() => new Promise(res => { const f = document.getElementById('layer-editor'); if (!f || !f.contentWindow) return res(); "
            "const h = e => { if (e.data && e.data.type === 'flushed') { removeEventListener('message', h); res(); } }; "
            "addEventListener('message', h); f.contentWindow.postMessage({type: 'flush'}, '*'); setTimeout(res, 5000); })")
# runs in the browser before do_edit: the editor saves its pending changes first (cuts, moves), then the inputs are passed on unchanged
FLUSH_ARGS_JS = "async (...args) => { await (" + FLUSH_JS + ")(); return args; }"


# ---------------------------------------------------------------------------- helpers
def err(e: Exception) -> str:
    traceback.print_exc()
    return f"**Error:** {type(e).__name__}: {e}"


def load(scene_id: str) -> Scene:
    return Scene.load(os.path.join(S.scenes_dir, scene_id, "scene.json"))


def scene_list():
    paths = sorted(glob.glob(os.path.join(S.scenes_dir, "*", "scene.json")), reverse=True)
    return [os.path.basename(os.path.dirname(p)) for p in paths]


def img_path(sc: Scene, file: str) -> str:
    return os.path.join(S.scenes_dir, sc.id, file)


def variant_tiles(sc: Scene, edits_of: str | None = None):
    """(layer id, variant index, picture path, caption). Default: the versions the splitter made, back to front.
    edits_of=<layer id>: the Qwen edit versions of that layer. The editor's own changes (mode `hand`) are never listed."""
    out = []
    for l in ENGINE._ordered(sc):
        if edits_of is not None and l.id != edits_of:
            continue
        for i, v in enumerate(l.variants):
            is_edit = v.mode.startswith("edit")
            if v.mode == "hand" or is_edit != (edits_of is not None):
                continue
            out.append((l.id, i, img_path(sc, v.file), f"{l.name} · version {len(out) + 1 if edits_of is not None else i + 1}"
                        + (" ✔ in use" if i == l.selected else "") + (" (failed the check)" if v.mode == "edit-unchecked" else "")))
    return out


def version_gallery(sc: Scene, edits_of: str | None = None):
    return [(p, cap) for _l, _i, p, cap in variant_tiles(sc, edits_of)]


def editor_html(sid: str | None) -> str:
    if not sid:
        return "<div style='padding:24px;opacity:.7'>The layer editor appears here after you split a picture or load a saved scene.</div>"
    return f"<iframe id='layer-editor' src='/editor?scene={sid}' style='width:100%;height:820px;border:1px solid #8884;border-radius:8px'></iframe>"


def flatten(img) -> Image.Image | None:
    """An ImageEditor value (dict with composite / background) or a PIL image -> RGB on white."""
    if img is None:
        return None
    if isinstance(img, dict):
        img = img.get("composite") or img.get("background")
        if img is None:
            return None
    img = img.convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.alpha_composite(img)
    return bg.convert("RGB")


# ---------------------------------------------------------------------------- servers
def role_line(role: str, label: str) -> str:
    try:
        st = kaggle_launch.poll(role)
    except Exception as e:  # noqa: BLE001
        return f"- **{label}:** status unknown ({type(e).__name__}: {e})"
    if st == "ready":
        info = connection.check(role="split" if role == "both" else role).get("info", {})
        lim, idle = info.get("idle_limit_minutes") or 0, int((info.get("idle_seconds") or 0) // 60)
        free = info.get("gpu_free_gib")
        return (f"- **{label}:** ✅ ready" + (f" · idle {idle} of {lim:g} min before it stops itself" if lim else "")
                + (f" · free GPU memory {free} GiB" if free else ""))
    if st == "off":
        return f"- **{label}:** off"
    return f"- **{label}:** " + (f"⏳ {st}" if st.startswith("starting") else f"❌ {st}")


def refresh_servers() -> str:
    ok, who = kaggle_launch.available()
    head = f"Kaggle account **{who}**." if ok else f"⚠️ Cannot start servers from here: {who}"
    lines = [role_line("both", "SDXL-Turbo + Qwen-Image-2.1 (one Kaggle session)")]
    if "✅" not in lines[0]:                                  # servers started separately
        lines += [l for l in (role_line("generate", "SDXL-Turbo only"), role_line("split", "Qwen-Image-2.1 only")) if not l.endswith("off")]
    alt = role_line("alt", "Other splitter session")
    if not alt.endswith("off"):
        lines.append(alt)
    return head + "\n\n" + "\n".join(lines)


def do_start(role: str, profile: str | None = None):
    try:
        return kaggle_launch.start(role, S.idle_minutes, profile=profile) + "\n\n" + refresh_servers()
    except Exception as e:  # noqa: BLE001
        return err(e) + "\n\n" + refresh_servers()


def do_stop(role: str):
    try:
        return kaggle_launch.stop(role) + "\n\n" + refresh_servers()
    except Exception as e:  # noqa: BLE001
        return err(e) + "\n\n" + refresh_servers()


def do_start_alt(label: str):
    prof, _method, role = SPLITTERS[label]
    if role != "alt":
        return do_start("both")
    return do_start("alt", prof)


# ---------------------------------------------------------------------------- 1. the picture
def _gallery(images):
    return [(im, f"version {i + 1}") for i, im in enumerate(images)]


def do_from_text(prompt, versions, seed, steps, progress=gr.Progress()):
    if not str(prompt).strip():
        return [], None, [], "Describe the scene first."
    try:
        ims = ENGINE.first_images(prompt, n=int(versions), seed=int(seed), steps=int(steps), progress=lambda m: progress(0, desc=m))
        return _gallery(ims), ims[0], ims, f"{len(ims)} picture(s) from SDXL-Turbo. Click a version to use it, then split it into layers below."
    except Exception as e:  # noqa: BLE001
        return [], None, [], err(e)


def do_from_sketch(sketch, prompt, versions, seed, steps, strength, progress=gr.Progress()):
    src = flatten(sketch)
    if src is None:
        return [], None, [], "Draw a sketch (or upload a picture to draw on) first."
    if not str(prompt).strip():
        return [], None, [], "Describe what the sketch should become."
    try:
        ims = ENGINE.first_images(prompt, n=int(versions), seed=int(seed), steps=int(steps), init=src, strength=float(strength),
                                  progress=lambda m: progress(0, desc=m))
        return _gallery(ims), ims[0], ims, f"{len(ims)} picture(s) from the sketch (strength {strength}). Click a version to use it."
    except Exception as e:  # noqa: BLE001
        return [], None, [], err(e)


def do_pick_version(cands, evt: gr.SelectData):
    return cands[evt.index] if cands and 0 <= evt.index < len(cands) else gr.skip()


# ---------------------------------------------------------------------------- 2. split
def method_of(label):
    return SPLITTERS.get(label, SPLITTERS[DEFAULT_SPLITTER])


def presets_of(label):
    prof, method, _ = method_of(label)
    out = []
    for p in PROFILES.values():
        for c in p.cases:
            if c.params.method == method:
                out.append((f"{'A best case' if c.path == 'A' else 'B live demo'}: {c.note}", asdict(c.params)))
    return out


def on_splitter(label):
    prof, method, role = method_of(label)
    need = NEEDS.get(method, set())
    pre = presets_of(label)
    hint = ("Runs in the main Kaggle session." if role == "split" else
            f"Needs its own Kaggle session (profile `{prof}`): press **Start this splitter** and wait for it to turn ready; "
            "it uses GPU quota while it runs, so stop it when done.")
    return (gr.update(visible="names" in need), gr.update(visible="boxes" in need), gr.update(visible="layers" in need),
            gr.update(visible="amodal" in need), gr.update(visible="sampler" in need),
            gr.update(choices=[l for l, _ in pre], value=pre[0][0] if pre else None), hint,
            gr.update(visible=role == "alt"))


def on_preset(label, preset):
    for l, p in presets_of(label):
        if l == preset:
            return p.get("resolution", 512), p.get("steps", 4), p.get("n_layers", 4), p.get("sampler", "euler"), bool(p.get("amodal", False))
    return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()


NO_SCENE = (None, editor_html(None), [])


def do_split(pic, prompt, label, names_csv, boxes_json, n_layers, res, steps, sampler, amodal, versions, progress=gr.Progress()):
    """Generator: the editor opens at once and every layer appears in it (and in the version row) as soon as it is made."""
    import json as _json
    if pic is None:
        yield (*NO_SCENE, "Make or upload a picture first.")
        return
    prof, method, role = method_of(label)
    names = [n.strip() for n in (names_csv or "").split(",") if n.strip()]
    need = NEEDS[method]
    if "names" in need and "boxes" not in need and not names:
        yield (*NO_SCENE, "Name the objects to extract, comma separated, back to front (e.g. cottage, big tree, red fox).")
        return
    try:
        boxes = _json.loads(boxes_json) if boxes_json and str(boxes_json).strip() else []     # hidden inputs arrive as None
    except (ValueError, TypeError) as e:
        yield (*NO_SCENE, f"The boxes are not valid JSON: {e}")
        return
    sc = Scene(id=new_scene_id(prompt or "scene"), user_input=prompt or "", refined_prompt=prompt or "", n_layers=int(n_layers))
    sc.save(S.scenes_dir)
    sid = sc.id

    def say(m):
        editor_api.set_generating(sid, m)
        progress(0, desc=m)

    editor_api.set_generating(sid, "starting the split")
    yield sid, editor_html(sid), [], "Making the layers; each one appears in the editor as soon as it is done."
    try:
        p = DecomposeParams(caption=prompt or "", method=method, n_layers=int(n_layers), boxes=boxes, names=names, amodal=bool(amodal),
                            resolution=int(res), steps=int(steps), sampler=sampler)
        for sc in ENGINE.split_stream(sc, pic.convert("RGB"), p, versions=int(versions), progress=say, role=role):
            yield sid, gr.skip(), version_gallery(sc), f"Scene `{sid}`: {len(sc.layers)} layer(s) so far."
        yield sid, gr.skip(), version_gallery(load(sid)), f"Scene `{sid}` done: {len(sc.layers)} layers. Work on them in the editor below."
    except Exception as e:  # noqa: BLE001
        yield sid, gr.skip(), version_gallery(load(sid)), err(e)
    finally:
        editor_api.set_generating(sid, None)


def do_load(name):
    if not name or name not in scene_list():
        return (*NO_SCENE[:1], editor_html(None), [], "Pick a saved scene.")
    sc = load(name)
    return sc.id, editor_html(sc.id), version_gallery(sc), f"Loaded `{sc.id}`."


# ---------------------------------------------------------------------------- 3. layers
def selected_layer(sid):
    return editor_api.selected(sid) if sid else None


def do_pick_variant(sid, evt: gr.SelectData):
    """A split version picked in the row under the split: it becomes that layer's picture in the editor."""
    if not sid:
        return gr.skip(), "Split a picture first."
    sc = load(sid)
    tiles = variant_tiles(sc)
    if not 0 <= evt.index < len(tiles):
        return gr.skip(), gr.skip()
    lid, idx = tiles[evt.index][:2]
    sc = ENGINE.select(sc, lid, idx)
    return version_gallery(sc), f"'{sc.layer(lid).name}': split version {idx + 1} is now the layer in the editor."


def do_pick_edit(sid, lid, evt: gr.SelectData):
    """An edit version picked in the row under 'Edit the picked layer'."""
    if not sid or not lid:
        return gr.skip(), gr.skip(), "Edit a layer first."
    sc = load(sid)
    tiles = variant_tiles(sc, lid)
    if not 0 <= evt.index < len(tiles):
        return gr.skip(), gr.skip(), gr.skip()
    sc = ENGINE.select(sc, lid, tiles[evt.index][1])
    return version_gallery(sc), version_gallery(sc, lid), f"Edit version {evt.index + 1} of '{sc.layer(lid).name}' is now the layer in the editor."


def do_edit(sid, prompt, versions, seed, progress=gr.Progress()):
    lid = selected_layer(sid)
    if not sid or not lid:
        return gr.skip(), gr.skip(), gr.skip(), "Pick a layer in the editor first (click it in the picture or in the layer list)."
    if not str(prompt).strip():
        return gr.skip(), gr.skip(), gr.skip(), "Describe the change."
    try:
        with ENGINE.lock:
            sc = load(sid)
        n_before = len(sc.layer(lid).variants)
        sc = ENGINE.edit_versions(sc, lid, str(prompt).strip(), versions=int(versions), seed=int(seed), progress=lambda m: progress(0, desc=m))
        l = sc.layer(lid)
        new = [v for v in l.variants[n_before:] if v.mode.startswith("edit")]
        ok = sum(v.mode == "edit" for v in new)
        if ok:
            note = f"Edited '{l.name}': {ok} of {len(new)} version(s) passed the check; the last good one is in the editor, the others are in the version row above."
        else:
            note = (f"⚠️ '{l.name}' was NOT changed: the {len(new)} edit(s) did not pass the transparency check (the result lost or flooded the layer). "
                    "They are in the version row above (marked failed); try another wording or seed.")
        return version_gallery(sc), version_gallery(sc, lid), lid, note
    except Exception as e:  # noqa: BLE001
        return gr.skip(), gr.skip(), gr.skip(), err(e)


# ---------------------------------------------------------------------------- layout
with gr.Blocks(title="Layer scene prototype") as demo:
    scene_id = gr.State(None)
    cands = gr.State([])
    gr.Markdown("# Layer scene prototype\nAll models run on a Kaggle GPU session that this app starts for you; nothing runs on this computer.")

    with gr.Accordion("Kaggle session", open=True):
        servers_md = gr.Markdown(refresh_servers())
        with gr.Row():
            both_start = gr.Button("Start (SDXL-Turbo + Qwen-Image-2.1)", variant="primary", scale=3)
            both_stop = gr.Button("Stop", scale=1)
        gr.Markdown("_Start uses your own Kaggle account (GPU hours count against its weekly quota, idle time too). "
                    f"The session stops itself after {S.idle_minutes:g} idle minutes; **Stop** ends it at once, also while it is still loading._")
        with gr.Accordion("Separate sessions (one model each)", open=False):
            with gr.Row():
                gen_start = gr.Button("Start SDXL-Turbo only")
                gen_stop = gr.Button("Stop SDXL-Turbo")
                spl_start = gr.Button("Start Qwen-Image-2.1 only")
                spl_stop = gr.Button("Stop Qwen-Image-2.1")
        timer = gr.Timer(6)
    both_start.click(lambda: do_start("both"), None, [servers_md])
    both_stop.click(lambda: do_stop("both"), None, [servers_md])
    gen_start.click(lambda: do_start("generate"), None, [servers_md])
    gen_stop.click(lambda: do_stop("generate"), None, [servers_md])
    spl_start.click(lambda: do_start("split"), None, [servers_md])
    spl_stop.click(lambda: do_stop("split"), None, [servers_md])
    timer.tick(refresh_servers, None, [servers_md])
    demo.load(refresh_servers, None, [servers_md])

    status = gr.Markdown()

    # ------------------------------------------------------------------ 1. picture
    gr.Markdown("## 1. The picture (SDXL-Turbo)")
    with gr.Row():
        with gr.Column(scale=3):
            prompt = gr.Textbox(label="Describe the scene", lines=3,
                                placeholder="storybook illustration of a stone cottage, a big tree on the right, a red fox on the path")
            with gr.Row():
                versions1 = gr.Slider(1, 4, value=2, step=1, label="Versions (different seeds)")
                seed = gr.Number(S.first_seed, label="First seed", precision=0)
                steps = gr.Slider(1, 8, value=S.first_steps, step=1, label="SDXL-Turbo steps")
            sketch = gr.ImageEditor(label="Sketch (draw, or upload a picture and draw on it) for image to image", type="pil",
                                    canvas_size=(512, 512), sources=["upload", "clipboard"], height=420,
                                    brush=gr.Brush(default_size=6, colors=["#000000", "#d62828", "#2a9d3f", "#1d4ed8", "#f2c200", "#ffffff"], default_color="#000000"),
                                    eraser=gr.Eraser(default_size=20))
            with gr.Row():
                strength = gr.Slider(0.3, 0.95, value=0.8, step=0.05, label="Sketch strength (higher = the sketch guides less)")
            with gr.Row():
                text_btn = gr.Button("Make the picture from the text", variant="primary")
                sketch_btn = gr.Button("Make the picture from the sketch (image to image)", variant="primary")
        with gr.Column(scale=2):
            pic = gr.Image(label="Picture to split (click a version below, or upload your own)", type="pil", height=420)
            cand_gallery = gr.Gallery(label="Versions (click to use)", columns=4, height=170, allow_preview=False)
    text_btn.click(do_from_text, [prompt, versions1, seed, steps], [cand_gallery, pic, cands, status])
    sketch_btn.click(do_from_sketch, [sketch, prompt, versions1, seed, steps, strength], [cand_gallery, pic, cands, status])
    cand_gallery.select(do_pick_version, [cands], [pic])

    # ------------------------------------------------------------------ 2. split
    gr.Markdown("## 2. Split into layers")
    with gr.Row():
        splitter = gr.Dropdown(list(SPLITTERS), value=DEFAULT_SPLITTER, label="Splitter", scale=3)
        preset = gr.Dropdown([], label="Preset (benchmark path A best case / B live demo)", scale=3)
        versions2 = gr.Slider(1, 4, value=1, step=1, label="Versions per layer (repeats the split with other seeds)", scale=2)
    alt_row = gr.Row(visible=False)
    with alt_row:
        alt_start = gr.Button("Start this splitter's Kaggle session")
        alt_stop = gr.Button("Stop it")
    hint = gr.Markdown()
    names_csv = gr.Textbox(label="Objects to extract, comma separated, back to front", placeholder="cottage, big tree, red fox")
    boxes_json = gr.Textbox(label="Boxes in pixels, back to front: [[x0,y0,x1,y1], ...] (RevealLayer and CLD need them; optional for SAM2)", lines=2, visible=False)
    with gr.Row():
        n_layers = gr.Slider(2, 8, value=4, step=1, label="Layers", visible=False)
        res = gr.Number(512, label="Resolution (px)", precision=0)
        steps2 = gr.Number(4, label="Steps", precision=0)
        sampler = gr.Dropdown(["euler", "heun"], value="euler", label="Sampler", visible=False)
        amodal = gr.Checkbox(False, label="Complete hidden parts (SDXL-inpaint, about 30 s per hidden object)", visible=False)
    with gr.Row():
        split_btn = gr.Button("Split the picture into layers", variant="primary", scale=3)
        old = gr.Dropdown(scene_list(), label="…or load a saved scene", scale=2)
        load_btn = gr.Button("Load", scale=1)
    on_out = [names_csv, boxes_json, n_layers, amodal, sampler, preset, hint, alt_row]
    splitter.change(on_splitter, [splitter], on_out)
    demo.load(on_splitter, [splitter], on_out)
    preset.input(on_preset, [splitter, preset], [res, steps2, n_layers, sampler, amodal])
    alt_start.click(do_start_alt, [splitter], [servers_md])
    alt_stop.click(lambda: do_stop("alt"), None, [servers_md])

    # ------------------------------------------------------------------ 3. layers, then the editor
    variants = gr.Gallery(label="Versions (click to use): what the split made for each layer", columns=4, rows=1, height=360,
                          object_fit="contain", allow_preview=False)

    gr.Markdown("## 3. Work on the layers")
    gr.Markdown("**Final image and layer editor.** Click a layer in the picture or the list. **Move** drags the layer (corner handles resize, the round handle rotates); "
                "**Rectangle / lasso** select an area of the active layer: drag inside it to move just that part within the layer, "
                "*Delete selected part* removes it from the layer (for objects the splitter put on the wrong layer), *Cut to new layer* makes a layer of it. "
                "Everything is saved as you go; *Export PNG* downloads the composite.")
    editor = gr.HTML(editor_html(None))
    with gr.Row():
        edit_prompt = gr.Textbox(label="Change the picked layer (Qwen-Image-2.1 edit, about 25 s per version)", lines=2, scale=4,
                                 placeholder="make the fox white / lit by a lantern from the left")
        versions3 = gr.Slider(1, 4, value=1, step=1, label="Versions", scale=1)
        edit_seed = gr.Number(42, label="Seed", precision=0, scale=1)
        edit_btn = gr.Button("Edit the picked layer", variant="primary", scale=2)
    edit_gallery = gr.Gallery(label="Versions (click to use): the edits of the picked layer", columns=4, rows=1, height=360,
                              object_fit="contain", allow_preview=False)
    edit_status = gr.Markdown()
    edit_lid = gr.State(None)

    split_btn.click(do_split, [pic, prompt, splitter, names_csv, boxes_json, n_layers, res, steps2, sampler, amodal, versions2],
                    [scene_id, editor, variants, status])
    load_btn.click(do_load, [old], [scene_id, editor, variants, status])
    edit_btn.click(do_edit, [scene_id, edit_prompt, versions3, edit_seed], [variants, edit_gallery, edit_lid, edit_status], js=FLUSH_ARGS_JS)         .then(None, None, None, js=EDITOR_JS)
    variants.select(do_pick_variant, [scene_id], [variants, edit_status]).then(None, None, None, js=EDITOR_JS)
    edit_gallery.select(do_pick_edit, [scene_id, edit_lid], [variants, edit_gallery, edit_status]).then(None, None, None, js=EDITOR_JS)

def build_app():
    """FastAPI app with the editor routes next to the Gradio UI (the editor and its pictures are plain routes, not Gradio components)."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(editor_api.make_router(ENGINE))
    return gr.mount_gradio_app(app, demo.queue(), path="/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(build_app(), host="127.0.0.1", port=int(os.environ.get("LAYERPROTO_PORT", "7870")), log_level="warning")
