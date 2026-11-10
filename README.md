# TTRPG Layered Scene Builder

Collaborative, layer-based image generation for tabletop role-playing games.
A group describes a scene together, the AI splits it into layers (one prompt per layer),
and players can move, re-prompt or regenerate single layers as the story moves on.

Research focus: **controllability** and layer-by-layer editing.

## Requirements

- [Node.js](https://nodejs.org) 20 or newer
- [Python](https://python.org) 3.11 or newer
- [Git](https://git-scm.com)

## Setup

### 1. Clone

```bash
git clone https://github.com/<your-username>/ttrpg-layered-scenes.git
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

> **Windows: "running scripts is disabled on this system"?**
> Run this once in PowerShell, then activate again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

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

## Adding dependencies

- **Frontend:** `npm install <package>` inside `frontend/`. This updates `package.json`
  automatically; commit `package.json` and `package-lock.json`.
- **Backend:** with the virtual environment active, `pip install <package>`, then
  `pip freeze > requirements.txt` and commit `requirements.txt`.

## Do not commit

`node_modules/`, `.venv/`, `__pycache__/` and `.env` (real API keys) are ignored by `.gitignore`.
Everyone recreates them locally with `npm install` and `pip install -r requirements.txt`.
