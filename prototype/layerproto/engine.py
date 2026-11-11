"""Scene engine: a thin client around the two Kaggle GPU servers plus the layer stack kept on this machine.

    first picture  = SDXL-Turbo on the `generate` server (text to image; image to image to restyle)
    split          = Qwen-Image-2.1 on the `split` server: image -> background + one RGBA layer per named object
    edit a layer   = Qwen-Image-2.1 RGBA edit on the `split` server (alpha check and retry), stored as a new variant
    move / resize  = canvas transform on the stored RGBA layer (dx, dy, scale); no model call
    final image    = background + every visible layer, bottom to top, with transforms

No model runs on this machine. The servers are started and stopped from the app (layerproto/kaggle_launch.py).
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from PIL import Image

from . import connection
from .backends import client
from .backends.decomposer import DecomposeParams, Decomposer, RemoteDecomposer
from .config import Settings
from .layer_edit import transparent_share
from .scene import Layer, Scene, Variant, slug

Progress = Optional[Callable[[str], None]]


class Engine:
    def __init__(self, settings: Settings):
        self.s = settings

    def reconfigure(self, settings: Settings) -> None:
        self.s = settings

    def decomposer_for(self, role: str = "split") -> Decomposer | None:
        """The splitter server of a role (split = Qwen-Image-2.1, alt = another profile), looked up at every use."""
        c = connection.load(role)
        return RemoteDecomposer(c.url, c.token) if c.configured else None

    @property
    def decomposer(self) -> Decomposer | None:
        return self.decomposer_for("split")

    def remote_methods(self) -> dict:
        """What the split server offers right now (profile, methods, presets); {} when none is configured."""
        from .backends.decomposer import remote_methods
        c = connection.load("split")
        if not c.configured:
            return {}
        try:
            return remote_methods(c.url, c.token)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    # ---- first picture ------------------------------------------------------------------------------
    def first_image(self, prompt: str, seed: int | None = None, steps: int | None = None, init: Image.Image | None = None,
                    strength: float = 0.5, progress: Progress = None) -> Image.Image:
        """SDXL-Turbo on the generate server; `init` makes it image to image (a regeneration, not an edit)."""
        self._say(progress, "SDXL-Turbo: " + ("image to image" if init is not None else "text to image"))
        seed = self.s.first_seed if seed is None else int(seed)
        steps = int(steps or self.s.first_steps)
        if init is not None:
            return client.img2img(init, prompt, strength=strength, seed=seed, steps=steps, size=self.s.width)
        return client.txt2img(prompt, seed=seed, steps=steps, size=self.s.width)

    # ---- image -> layers ---------------------------------------------------------------------------
    def import_layers(self, scene: Scene, layers: list[Image.Image], names: list[str] | None = None,
                      source: str = "decomposed") -> Scene:
        """Replace the scene's layers with an RGBA stack (background first). Each layer gets one variant, mode=`source`."""
        names = names or []
        scene.layers = []
        for i, img in enumerate(layers):
            name = names[i - 1] if i > 0 and i - 1 < len(names) else ("background" if i == 0 else f"layer {i}")
            lid = slug(name)
            while any(l.id == lid for l in scene.layers):
                lid += "x"
            layer = Layer(id=lid, name=name, role="background" if i == 0 else "object", depth=i, prompt=name)
            scene.layers.append(layer)
            rgba = img.convert("RGBA").resize((self.s.width, self.s.height))
            rel = scene.save_image(self.s.scenes_dir, layer, rgba, f"v00-{source}")
            hist = rgba.split()[-1].histogram()
            layer.variants.append(Variant(file=rel, seed=0, prompt=name, mode=source,
                                          transparent_pct=round(100 * sum(hist[:10]) / max(1, sum(hist)), 1)))
        scene.save(self.s.scenes_dir)
        return scene

    def decompose_image(self, scene: Scene, image: Image.Image, params: DecomposeParams | None = None,
                        progress: Progress = None, role: str = "split") -> Scene:
        """Send `image` to the splitter server of `role` and turn the returned RGBA stack into this scene's layers."""
        self._role = role
        if self.decomposer_for(role) is None:
            raise client.NotConnected(f"Not connected to the split server. {client.HOW['split']}")
        p = params or DecomposeParams(caption=scene.refined_prompt or scene.user_input, n_layers=scene.n_layers)
        self._say(progress, f"splitting with {p.method} (remote GPU)")
        t0 = time.time()
        layers = self.decomposer_for(role).decompose(image, p)
        self._say(progress, f"{len(layers)} layers in {time.time() - t0:.0f} s")
        return self.import_layers(scene, layers, p.names, source=p.method)

    # ---- edit one layer ----------------------------------------------------------------------------
    def edit_layer(self, scene: Scene, layer_id: str, prompt: str, seed: int = 42, progress: Progress = None) -> Scene:
        """Re-prompt / relight one layer with the Qwen-Image-2.1 RGBA edit; the result becomes a new variant and is selected.
        An edit that wiped or flooded the layer is retried with other seeds on the server; if none passed, the closest one is
        kept as a variant (mode `edit-unchecked`) so the user can still look at it."""
        layer = scene.layer(layer_id)
        v = layer.current()
        if v is None:
            raise ValueError("this layer has no image yet")
        cur = Image.open(f"{scene.folder(self.s.scenes_dir)}/{v.file}").convert("RGBA")
        self._say(progress, f"{layer.name}: Qwen-Image-2.1 edit")
        t0 = time.time()
        out, report = client.edit_layer(cur, prompt, seed)
        rel = scene.save_image(self.s.scenes_dir, layer, out, f"v{len(layer.variants):02d}-edit-{seed}")
        layer.variants.append(Variant(file=rel, seed=seed, prompt=prompt, mode="edit" if report.get("accepted", True) else "edit-unchecked",
                                      seconds=round(time.time() - t0, 1), transparent_pct=round(100 * transparent_share(out), 1)))
        layer.selected = len(layer.variants) - 1
        scene.save(self.s.scenes_dir)
        return scene

    # ---- several versions ---------------------------------------------------------------------------
    def first_images(self, prompt: str, n: int = 1, seed: int | None = None, steps: int | None = None, init: Image.Image | None = None,
                     strength: float = 0.8, progress: Progress = None) -> list[Image.Image]:
        """n pictures from SDXL-Turbo with consecutive seeds; `init` (a sketch or a picture) makes it image to image."""
        base = self.s.first_seed if seed is None else int(seed)
        out = []
        for k in range(max(1, int(n))):
            self._say(progress, f"SDXL-Turbo picture {k + 1} of {int(n)} (seed {base + k})")
            out.append(self.first_image(prompt, seed=base + k, steps=steps, init=init, strength=strength))
        return out

    def add_variant(self, scene: Scene, layer: Layer, img: Image.Image, mode: str, seed: int = 0, prompt: str = "", secs: float = 0.0) -> Variant:
        rgba = img.convert("RGBA").resize((self.s.width, self.s.height))
        rel = scene.save_image(self.s.scenes_dir, layer, rgba, f"v{len(layer.variants):02d}-{mode}-{seed}")
        v = Variant(file=rel, seed=seed, prompt=prompt or layer.prompt, mode=mode, seconds=round(secs, 1),
                    transparent_pct=round(100 * transparent_share(rgba), 1))
        layer.variants.append(v)
        return v

    def split_versions(self, scene: Scene, image: Image.Image, params: DecomposeParams, versions: int = 1, progress: Progress = None,
                       role: str = "split") -> Scene:
        """Split `image`; with versions > 1 the split is repeated with other seeds and every layer gets one variant per run."""
        self.decompose_image(scene, image, params, progress, role=role)
        for k in range(1, max(1, int(versions))):
            self._say(progress, f"split version {k + 1} of {int(versions)}")
            p = DecomposeParams(**{**params.__dict__, "seed": params.seed + k})
            layers = self.decomposer_for(role).decompose(image, p)
            for layer, img in zip(scene.layers, layers):
                self.add_variant(scene, layer, img, params.method, seed=p.seed)
        scene.save(self.s.scenes_dir)
        return scene

    def edit_versions(self, scene: Scene, layer_id: str, prompt: str, versions: int = 1, seed: int = 42, progress: Progress = None) -> Scene:
        for k in range(max(1, int(versions))):
            self.edit_layer(scene, layer_id, prompt, seed=seed + 1000 * k, progress=progress)
        return scene

    # ---- the canvas editor (ui/editor.html) saves its whole state here --------------------------------
    def apply_editor_state(self, scene: Scene, state: dict) -> Scene:
        """state = {layers: [{id, name, visible, dx, dy, scale, rot, png?}], selected}, bottom to top (the background first).
        A layer with `png` (a data URL of its full canvas, RGBA) was changed pixel-wise (cut a selection out of it, or created by
        cutting): it gets a new variant (mode `hand`). Layers missing from the list are removed; the order sets the depth."""
        import base64
        import io
        old = {l.id: l for l in scene.layers}
        new_layers = []
        for depth, d in enumerate(state.get("layers", [])):
            lid = str(d["id"])
            layer = old.get(lid)
            if layer is None:                                   # created in the editor by cutting a selection
                base_id = slug(str(d.get("name") or "layer"))
                lid = base_id
                while lid in old or any(l.id == lid for l in new_layers):
                    lid += "x"
                layer = Layer(id=lid, name=str(d.get("name") or "layer"), role="object", depth=depth, prompt=str(d.get("name") or "layer"))
            png = d.get("png")
            if png:
                raw = base64.b64decode(png.split(",", 1)[1] if "," in png else png)
                self.add_variant(scene, layer, Image.open(io.BytesIO(raw)), "hand", seed=len(layer.variants))
                layer.selected = len(layer.variants) - 1
            layer.enabled = bool(d.get("visible", True))
            layer.dx, layer.dy = float(d.get("dx", 0.0)), float(d.get("dy", 0.0))
            layer.scale, layer.rot = max(0.05, float(d.get("scale", 1.0))), float(d.get("rot", 0.0))
            layer.depth = depth
            new_layers.append(layer)
        if new_layers and new_layers[0].role != "background":
            pass                                                # a scene without a background keeps its first layer as it is
        scene.layers = new_layers
        scene.save(self.s.scenes_dir)
        return scene

    # ---- composition (Photoshop-style stack) --------------------------------------------------------
    def _ordered(self, scene: Scene) -> list[Layer]:
        return sorted(scene.layers, key=lambda l: (l.role != "background", l.depth))

    def object_order(self, scene: Scene) -> list[Layer]:
        """Element layers from bottom to top."""
        return [l for l in self._ordered(scene) if l.role != "background"]

    def move_layer(self, scene: Scene, layer_id: str, direction: str) -> Scene:
        order = self.object_order(scene)
        i = next(k for k, l in enumerate(order) if l.id == layer_id)
        j = i + 1 if direction == "up" else i - 1
        if 0 <= j < len(order):
            order[i], order[j] = order[j], order[i]
        for depth, l in enumerate(order, start=1):
            l.depth = depth
        scene.layers = [l for l in scene.layers if l.role == "background"] + order
        scene.save(self.s.scenes_dir)
        return scene

    def transform_layer(self, scene: Scene, layer_id: str, dx: float, dy: float, scale: float, rot: float = 0.0) -> Scene:
        layer = scene.layer(layer_id)
        layer.dx, layer.dy, layer.scale, layer.rot = float(dx), float(dy), max(0.05, float(scale)), float(rot)
        scene.save(self.s.scenes_dir)
        return scene

    def fit_layer_to_box(self, scene: Scene, layer_id: str, box: list | None = None) -> Scene:
        """Move and resize an element so its visible content fills the layer's planned box [x, y, w, h] (0..1), keeping the
        aspect ratio and centring it in the box. Canvas transform only, no model call."""
        layer = scene.layer(layer_id)
        v = layer.current()
        if layer.role == "background" or v is None:
            return scene
        W, H = self.s.width, self.s.height
        bbox = Image.open(f"{scene.folder(self.s.scenes_dir)}/{v.file}").convert("RGBA").resize((W, H)).split()[-1].point(
            lambda a: 255 if a > 40 else 0).getbbox()
        if bbox is None:
            return scene
        bx, by, bw, bh = [float(x) for x in (box or layer.box)]
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        s_ = max(0.05, min(bw * W / w, bh * H / h))
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        # _placed keeps the visible centre fixed while scaling, then shifts by dx*W / dy*H
        return self.transform_layer(scene, layer_id, ((bx + bw / 2) * W - cx) / W, ((by + bh / 2) * H - cy) / H, s_)

    def fit_all_to_boxes(self, scene: Scene) -> Scene:
        for l in self._ordered(scene):
            if l.role != "background":
                self.fit_layer_to_box(scene, l.id)
        return scene

    def _placed(self, img: Image.Image, layer: Layer, W: int, H: int) -> Image.Image:
        """Apply a layer's move/resize to its full-canvas RGBA image."""
        img = img.convert("RGBA").resize((W, H))
        rot = getattr(layer, "rot", 0.0)
        if layer.dx == 0 and layer.dy == 0 and layer.scale == 1 and rot == 0:
            return img
        bbox = img.split()[-1].point(lambda a: 255 if a > 24 else 0).getbbox() or (0, 0, W, H)   # faint stray pixels do not count (same rule as ui/editor.html)
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2      # the visible centre: scale and rotation pivot
        if rot:                                                          # rotate around the pivot, canvas size kept
            img = img.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
        if layer.scale != 1:
            sw, sh = max(1, int(W * layer.scale)), max(1, int(H * layer.scale))
            scaled = img.resize((sw, sh), Image.LANCZOS)
            ox, oy = int(cx - cx * layer.scale), int(cy - cy * layer.scale)  # keep the visible centre in place
        else:
            scaled, ox, oy = img, 0, 0
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.paste(scaled, (ox + int(layer.dx * W), oy + int(layer.dy * H)))
        return out

    def compose(self, scene: Scene, below_depth: int | None = None, save: bool = True) -> Image.Image:
        """Stack the selected variants. below_depth: only the background and elements under that depth."""
        folder = scene.folder(self.s.scenes_dir)
        W, H = self.s.width, self.s.height
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        for l in self._ordered(scene):
            if l.role != "background" and below_depth is not None and l.depth >= below_depth:
                continue
            v = l.current()
            if not (l.enabled and v):
                continue
            canvas.alpha_composite(self._placed(Image.open(f"{folder}/{v.file}"), l, W, H))
        if save and below_depth is None:
            canvas.save(f"{folder}/final.png")
        return canvas

    def select(self, scene: Scene, layer_id: str, index: int) -> Scene:
        layer = scene.layer(layer_id)
        layer.selected = max(0, min(index, len(layer.variants) - 1))
        scene.save(self.s.scenes_dir)
        return scene

    @staticmethod
    def _say(progress: Progress, msg: str):
        if progress:
            progress(msg)
