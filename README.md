# TTRPG Layered Scene Builder

Collaborative, layer-based image generation for tabletop role-playing games.
A group describes a scene together, the AI splits it into layers (one prompt per layer),
and players can move, re-prompt or regenerate single layers as the story moves on.

Research focus: **controllability** and layer-by-layer editing.

## Important links

- [Project proposal](https://docs.google.com/document/d/1Lz25EpAJJpKTYKxB1rv7MB7iUOGeFCib-3zZxW-ZP-4/edit): research questions and interaction flow
- [FastSD CPU: Install and Offline Setup](https://docs.google.com/document/d/1yIu7I4X1hpMfRusVPDoD5JyGqKqsgRSXyvXDhRV0Pdw/edit): local CPU image generation with SD-Turbo / SDXL-Turbo, no GPU or internet needed after setup
- [FastSD CPU: Prompts and Settings](https://docs.google.com/document/d/1OmJISs_dD3YFeTmEjd9xWLOZPMlfccUEBaCypkj984A/edit): how to write prompts and which settings to use for Text to Image and Image to Image

## Two ways to start

The repository holds two front ends for the same idea. They do not depend on each other yet.

| | A. React + FastAPI (team app) | B. Gradio prototype (`prototype/`) |
|---|---|---|
| What it is | The product front end and API, being built | A working thin client for the loop prompt or sketch, picture, layers, edit layers, recomposite |
| Models | none yet | none on your computer; SDXL-Turbo and Qwen-Image-2.1 run in a Kaggle GPU session the app starts and stops with your own Kaggle account |
| Start | steps 2 and 3 under Setup below | [prototype/README.md](prototype/README.md): `pip install -r prototype/requirements.txt`, then `python prototype/app.py` and open http://127.0.0.1:7870 |
| Needs | Node.js, Python | Python 3.10+, a phone-verified Kaggle account and API token |

Start with [docs/handoff.md](docs/handoff.md) for the project, the evidence and what to build next, [docs/status.md](docs/status.md) for what works today and [docs/todo.md](docs/todo.md) for open work. The prototype's code arrives in the following pull requests of the stack (see the open issues).

## Requirements

- [Node.js](https://nodejs.org) 20 or newer
- [Python](https://python.org) 3.11 or newer

## Setup

### 1. Clone

```bash
git clone https://github.com/CubePillow/ttrpg-layered-scenes.git
cd ttrpg-layered-scenes
```

### 2. Frontend (React + TypeScript + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 3. Backend (FastAPI) – in a second terminal

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env          # Windows  (macOS / Linux: cp .env.example .env)
uvicorn main:app --reload
```

The API runs at http://localhost:8000. Check http://localhost:8000/health
and the interactive API docs at http://localhost:8000/docs.


## Project structure

```
ttrpg-layered-scenes/
├── frontend/          React + TypeScript + Vite (layer canvas, UI)
│   └── src/
├── backend/           FastAPI (layer generation, word breakdown)
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── .gitignore
└── README.md
```

