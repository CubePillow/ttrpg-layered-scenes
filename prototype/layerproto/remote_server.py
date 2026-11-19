"""HTTP server for the GPU side (a Kaggle notebook behind a tunnel, Modal, ...): one model profile per server.

    python -m layerproto.remote_server --port 8765 --token <secret>        (the LayerDiffuse chain; optional profile)

Endpoints (JSON, images as base64 PNG). Every route except /health needs the X-Token header.
    GET  /health           -> {role: "generate" | "split" | "both" (studio), profile, idle_seconds, idle_limit_minutes, ...}   (does not count as activity)
    GET  /methods          -> {profile, methods: [{method, presets: [{label, path, params}]}]}   (only with a decomposer)
    POST /decompose        {params, image} -> {layers: [b64 PNG, background first]}   (only with a decomposer)
    POST /edit             {image, prompt, seed} -> {image, report}   (RGBA layer edit with alpha check; only with an editor)
    POST /txt2img          {prompt, seed, steps, size, negative} -> {image}                    (only with a generator: sdxl-turbo)
    POST /img2img          {image, prompt, strength, seed, steps, size, negative} -> {image}   (only with a generator)
    POST /shutdown         ends the server (and so the batch kernel); this also happens by itself after `idle_minutes` without a request
    POST /chain/background | /chain/blend | /chain/extract | /chain/relocate      (LayerDiffuse chain, optional)
The app starts and stops the notebooks (layerproto/kaggle_launch.py); the connection line a notebook prints
(`LAYERPROTO-CONNECT <url>|<token>`) can also be pasted by hand (layerproto/connection.py).
"""
from __future__ import annotations

import argparse
import threading
import time

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .backends.chain_base import ChainParams
from .backends.remote import b64_to_img, img_to_b64


class RelocateReq(BaseModel):
    params: dict
    scene: str              # canvas without the layer (RGB)
    layer: str              # the layer's RGBA (canvas-sized)
    box: list               # new [x, y, w, h] in pixels for the layer's visible content
    strength: float = 0.5
    pin_frac: float = 0.4


class DecomposeReq(BaseModel):
    params: dict
    image: str


class EditReq(BaseModel):
    image: str
    prompt: str
    seed: int = 42


class GenReq(BaseModel):
    prompt: str
    image: str | None = None
    strength: float = 0.75
    seed: int = 13
    steps: int = 4
    size: int = 512
    negative: str = ""


class Req(BaseModel):
    params: dict
    scene: str | None = None
    blended: str | None = None


def describe_methods(decomposer, profile: str | None) -> dict:
    """Methods the loaded decomposer offers, with the presets (benchmark paths A / B) of the running profile for the frontend."""
    from dataclasses import asdict
    names = sorted(getattr(decomposer, "by_method", {}) or [])
    presets: dict[str, list] = {}
    if profile:
        try:
            from .serve.profiles import PROFILES
            for c in PROFILES[profile].cases:
                params = {k: v for k, v in asdict(c.params).items() if k in ("method", "resolution", "n_layers", "steps", "sampler", "amodal")}
                label = f"{'A best case' if c.path == 'A' else 'B live demo (~30 s)'}: {c.note}"
                presets.setdefault(c.params.method, []).append({"label": label, "path": c.path, "params": params})
        except Exception:  # noqa: BLE001 - presets are optional
            pass
    names = names or sorted(presets)
    return {"profile": profile, "methods": [{"method": m, "presets": presets.get(m, [])} for m in names]}


def build_app(chain, token: str = "", decomposer=None, profile: str | None = None, generator=None, editor=None,
              idle_minutes: float = 0, on_shutdown=None) -> FastAPI:
    """chain: LayerDiffuse chain or None (only its info() and the /chain routes use it).
    decomposer: callable (PIL image, DecomposeParams) -> list of RGBA PIL images, background first.
    generator: object with txt2img(prompt, seed, steps, size, negative) and
               img2img(image, prompt, strength, seed, steps, size, negative), both returning a PIL image.
    editor: callable (RGBA PIL image, prompt, seed) -> (edited RGBA image, report dict).
    idle_minutes is only reported; the caller watches `app.state.idle_seconds()` and ends the process (serve/launch.py).
    /shutdown calls on_shutdown() one second after answering."""
    app = FastAPI(title="layerproto server")
    state = {"last": time.time()}
    app.state.idle_seconds = lambda: time.time() - state["last"]
    role = "both" if (generator is not None and decomposer is not None) else "generate" if generator is not None else "split"

    def check(x_token, touch: bool = True):
        if token and x_token != token:
            raise HTTPException(401, "bad token")
        if touch:
            state["last"] = time.time()

    @app.get("/health")
    def health(x_token: str | None = Header(default=None)):
        check(x_token, touch=False)               # status polling by the app must not keep an idle server alive
        info = dict(chain.info()) if chain is not None else {}
        info.update(role=role, profile=profile, idle_seconds=round(app.state.idle_seconds()), idle_limit_minutes=idle_minutes)
        try:                                                   # free / total GiB per GPU, to see how tight a shared session is
            import torch
            if torch.cuda.is_available():
                info["gpu_free_gib"] = [round(torch.cuda.mem_get_info(i)[0] / 2**30, 1) for i in range(torch.cuda.device_count())]
        except Exception:  # noqa: BLE001
            pass
        return info

    @app.post("/shutdown")
    def shutdown(x_token: str | None = Header(default=None)):
        check(x_token)
        if on_shutdown is not None:
            threading.Timer(1.0, on_shutdown).start()      # let this response go out first
        return {"ok": True}

    if generator is not None:
        @app.post("/txt2img")
        def txt2img(req: GenReq, x_token: str | None = Header(default=None)):
            check(x_token)
            return {"image": img_to_b64(generator.txt2img(req.prompt, req.seed, req.steps, req.size, req.negative))}

        @app.post("/img2img")
        def img2img(req: GenReq, x_token: str | None = Header(default=None)):
            check(x_token)
            if not req.image:
                raise HTTPException(400, "img2img needs an image")
            return {"image": img_to_b64(generator.img2img(b64_to_img(req.image).convert("RGB"), req.prompt, req.strength,
                                                          req.seed, req.steps, req.size, req.negative))}

    if editor is not None:
        @app.post("/edit")
        def edit(req: EditReq, x_token: str | None = Header(default=None)):
            check(x_token)
            out, report = editor(b64_to_img(req.image), req.prompt, req.seed)
            return {"image": img_to_b64(out), "report": report}

    if chain is not None and hasattr(chain, "background"):          # the LayerDiffuse chain (optional profile)
        @app.post("/chain/background")
        def background(req: Req, x_token: str | None = Header(default=None)):
            check(x_token)
            return {"image": img_to_b64(chain.background(ChainParams(**req.params)))}

        @app.post("/chain/blend")
        def blend(req: Req, x_token: str | None = Header(default=None)):
            check(x_token)
            return {"image": img_to_b64(chain.blend(b64_to_img(req.scene), ChainParams(**req.params)))}

        @app.post("/chain/extract")
        def extract(req: Req, x_token: str | None = Header(default=None)):
            check(x_token)
            img = chain.extract(b64_to_img(req.scene), b64_to_img(req.blended), ChainParams(**req.params))
            return {"image": img_to_b64(img)}

        @app.post("/chain/relocate")
        def relocate(req: RelocateReq, x_token: str | None = Header(default=None)):
            check(x_token)
            if not hasattr(chain, "relocate"):
                raise HTTPException(501, "this chain has no relocate()")
            p = ChainParams(**req.params)
            _naive, harm, new_layer = chain.relocate(b64_to_img(req.scene), b64_to_img(req.layer), req.box, p.prompt, p.seed,
                                                     strength=req.strength, pin_frac=req.pin_frac, w=p.width, h=p.height,
                                                     steps=p.steps, guidance=p.guidance, negative=p.negative_prompt)
            return {"layer": img_to_b64(new_layer), "composite": img_to_b64(harm)}

    if decomposer is not None:
        from .backends.decomposer import DecomposeParams

        @app.get("/methods")
        def methods(x_token: str | None = Header(default=None)):
            check(x_token)
            return describe_methods(decomposer, profile)

        @app.post("/decompose")
        def decompose(req: DecomposeReq, x_token: str | None = Header(default=None)):
            check(x_token)
            try:
                layers = decomposer(b64_to_img(req.image).convert("RGB"), DecomposeParams(**req.params))
            except ValueError as e:                      # unknown method, no names, nothing found: the caller's input, not a crash
                raise HTTPException(400, str(e))
            return {"layers": [img_to_b64(L) for L in layers]}

    return app


if __name__ == "__main__":
    import uvicorn

    from .backends.layerdiffuse_chain import LayerDiffuseChain

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stabilityai/stable-diffusion-xl-base-1.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--token", default="")
    ap.add_argument("--alpha-quality", default="best")
    a = ap.parse_args()
    uvicorn.run(build_app(LayerDiffuseChain(model=a.model, alpha_quality=a.alpha_quality), a.token),
                host=a.host, port=a.port)
