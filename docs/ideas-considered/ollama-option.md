# Optional idea: a language model for prompt planning (Ollama / API), dropped from the app for now

> **Role: concept / parked option.** The app used to call a local language model (Ollama `qwen3:4b`) to refine the player's text, split it into layers and break it into words and relations, plus a local vision model (`qwen2.5vl:3b`) for captions. That code was removed on 2026-11-11 because the feature was largely unused and the install (Ollama plus two model downloads, 11 GB of RAM for the old local SDXL) was a barrier for the team. The current flow needs no language model: the player writes the scene, SDXL-Turbo draws it, the player names the objects to extract. Status of the whole pipeline: [../status.md](../status.md).

## What it did and what it was for

| Step | What the LLM did | Why it is not in the current flow |
|---|---|---|
| Prompt refinement | rewrote several players' keywords into one clean prompt and a shared style | SDXL-Turbo takes the text as written; the shared style can be part of the prompt |
| Layer split | listed the objects, their depth order and a rough box | the player names the objects (back to front); Qwen-Image-2.1 extracts them by name |
| Word and relation breakdown | word types and subject-relation-object triples | was only displayed |
| Captions and word check | a vision model described each generated layer and compared it with the layer's words | a visual check by the player is enough for the first draft |
| Story-event router | mapped an event ("heavy rain") to per-layer actions (keep, relight, reprompt, remove) | still in the repo as [`events.py`](../../prototype/layerproto/events.py), takes any object with `chat_json(system, user, schema)`; not called by the app |

## How to bring it back as an opt-in (sketch, not built)

1. **Where it should run:** not on the laptop CPU (the old planner took 30-110 s there). Options: a hosted API with an OpenAI-compatible endpoint (a key in an environment variable, never in the repo), or a third Kaggle profile (a 4-7 B instruct model in GGUF behind the same server code; Kaggle allows only two GPU sessions at once, so it would have to share the `qwen21` session or replace the `sdxl-turbo` one).
2. **Interface to restore:** one `plan(text) -> {objects: [{name, depth, box}], style}` call that fills the "Objects to extract" box of the Create tab; the box stays editable, so the planner only suggests. The JSON schema and prompt of the old planner are in git history (`prototype/layerproto/llm.py`, removed; see the commit before "Connection kept apart from settings", 2026-11-11).
3. **Story events:** `events.route_event(llm, event, layer_names)` already takes the LLM as an argument; wiring it needs the `/edit` route (done) and a loop that applies the plan per layer (`event_apply.py`).
4. **Switch:** a setting such as `planner: "none" | "openai"` with the base URL and the environment variable name; the default stays `none` so the app never needs it.

Reasoning for keeping it out: every extra service is another thing 7 team members must install and keep running, and the evidence so far ([../models/pipeline-plan.md](../models/pipeline-plan.md)) says the bottleneck is layer quality, not planning.
