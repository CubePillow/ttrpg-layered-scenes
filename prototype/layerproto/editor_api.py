"""Server side of the canvas layer editor (prototype/ui/editor.html), mounted next to the Gradio app (app.py).

The editor composites the layers itself in the browser, so moving, resizing, rotating or cutting never reloads the picture. It keeps
this server up to date: every change is autosaved here (`POST /api/scene/<id>/save`), which also tells the Gradio side which layer
is selected (`selected(scene_id)`), so "Edit the layer" works on what you clicked in the editor.

    GET  /editor?scene=<id>              the editor page
    GET  /api/scene/<id>                 layers bottom to top: id, name, role, visible, dx, dy, scale, rot, url; W, H; selected
    POST /api/scene/<id>/save            {selected, layers: [{id, name, visible, dx, dy, scale, rot, png?}]} -> the same list
    POST /api/scene/<id>/selected        {id}
    GET  /scenes/<id>/<file>             a layer picture
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from .scene import Scene

UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
_SELECTED: dict[str, str] = {}
_GENERATING: dict[str, str] = {}      # scene id -> what the split is doing now (the editor polls and adds layers as they arrive)


def selected(scene_id: str | None) -> str | None:
    return _SELECTED.get(scene_id or "")


def set_selected(scene_id: str, layer_id: str | None) -> None:
    if layer_id:
        _SELECTED[scene_id] = layer_id


def set_generating(scene_id: str, text: str | None) -> None:
    if text:
        _GENERATING[scene_id] = text
    else:
        _GENERATING.pop(scene_id, None)


def make_router(engine) -> APIRouter:
    r = APIRouter()

    def scene_path(sid: str) -> str:
        if not sid or "/" in sid or "\\" in sid or ".." in sid:
            raise HTTPException(400, "bad scene id")
        return os.path.join(engine.s.scenes_dir, sid, "scene.json")

    def describe(sc: Scene) -> dict:
        out = []
        for l in engine._ordered(sc):
            v = l.current()
            url = f"/scenes/{sc.id}/{v.file}?v={int(os.path.getmtime(os.path.join(engine.s.scenes_dir, sc.id, v.file)))}" if v else ""
            out.append(dict(id=l.id, name=l.name, role=l.role, visible=l.enabled, dx=l.dx, dy=l.dy, scale=l.scale,
                            rot=getattr(l, "rot", 0.0), url=url, variants=len(l.variants)))
        return dict(id=sc.id, W=engine.s.width, H=engine.s.height, layers=[o for o in out if o["url"]], selected=_SELECTED.get(sc.id), generating=_GENERATING.get(sc.id))

    @r.get("/editor", response_class=HTMLResponse)
    def editor():
        with open(os.path.join(UI_DIR, "editor.html"), encoding="utf-8") as f:
            return HTMLResponse(f.read(), headers={"Cache-Control": "no-store"})

    @r.get("/scenes/{sid}/{path:path}")
    def scene_file(sid: str, path: str):
        base = os.path.realpath(os.path.join(engine.s.scenes_dir, sid))
        full = os.path.realpath(os.path.join(base, path))
        if not full.startswith(base + os.sep) or not os.path.isfile(full):
            raise HTTPException(404)
        return FileResponse(full, headers={"Cache-Control": "no-store"})

    @r.get("/api/scene/{sid}")
    def get_scene(sid: str):
        p = scene_path(sid)
        if not os.path.exists(p):
            raise HTTPException(404, "no such scene")
        return describe(Scene.load(p))

    @r.post("/api/scene/{sid}/save")
    async def save_scene(sid: str, request: Request):
        p = scene_path(sid)
        if not os.path.exists(p):
            raise HTTPException(404, "no such scene")
        state = await request.json()
        with engine.lock:
            sc = engine.apply_editor_state(Scene.load(p), state, keep_unknown=sid in _GENERATING)
        set_selected(sid, state.get("selected"))
        return describe(sc)

    @r.post("/api/scene/{sid}/selected")
    async def post_selected(sid: str, request: Request):
        set_selected(sid, (await request.json()).get("id"))
        return {"ok": True}

    return r
