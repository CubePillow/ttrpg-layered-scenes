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

The repository holds two front ends for the same idea. The team app reuses the prototype's Kaggle launcher and model clients.

| | A. React + FastAPI (team app) | B. Gradio prototype (`prototype/`) |
|---|---|---|
| What it is | The product front end and API, being built | A working thin client for the loop prompt or sketch, picture, layers, edit layers, recomposite |
| Models | none on your computer; the backend connects to a Kaggle GPU session with SDXL-Turbo and Qwen-Image-2.1 when it starts | none on your computer; SDXL-Turbo and Qwen-Image-2.1 run in a Kaggle GPU session the app starts and stops with your own Kaggle account |
| Start | steps 2 to 4 under Setup below | [prototype/README.md](prototype/README.md): `pip install -r prototype/requirements.txt`, then `python prototype/app.py` and open http://127.0.0.1:7870 |
| Needs | Node.js, Python, a phone-verified Kaggle account and API token | Python 3.10+, a phone-verified Kaggle account and API token |

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

Save your Kaggle token first ([step 4](#4-connect-to-kaggle)), because the backend connects to Kaggle as soon as it starts.

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

### 4. Connect to Kaggle

The models run in a Kaggle GPU session, not on your computer. Everyone uses their own Kaggle account.

**Set up your account once**

1. Sign in at https://www.kaggle.com and verify your phone number in [Settings](https://www.kaggle.com/settings). Kaggle needs this for GPU and internet access.
2. In the **API** section of Settings, create a new token.
3. Save the token on your computer. Replace `YOUR_TOKEN` with your token:

   Windows (PowerShell):

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.kaggle"
   [IO.File]::WriteAllText("$env:USERPROFILE\.kaggle\access_token", "YOUR_TOKEN")
   ```

   macOS / Linux:

   ```bash
   mkdir -p ~/.kaggle
   printf '%s' 'YOUR_TOKEN' > ~/.kaggle/access_token
   chmod 600 ~/.kaggle/access_token
   ```

   If Kaggle gives you a `kaggle.json` file instead, put that file in the same `.kaggle` folder.

Never put your token in the repository or share it in chat.

**Connect**

Start the backend and open http://localhost:5173. The backend joins your running Kaggle session or starts a new one. The status box in the bottom right corner of the page shows the progress, and the backend terminal prints each step with `[kaggle]`.

| Progress | What is happening |
|---|---|
| 5% | Checking your Kaggle account |
| 10–20% | Looking for a running session, or sending the notebook to Kaggle |
| 20–95% | Kaggle is loading the models (estimated from the time passed) |
| 97% | Checking both models |
| **100%** | **SDXL-Turbo and Qwen-Image-2.1 are ready to use** |

A new session usually takes 5 to 12 minutes, and longer when Kaggle has a queue.

**GPU quota**

A running session uses your weekly Kaggle GPU quota, including idle time. When you are done, open the status box and press **Stop session**. Otherwise the session stops by itself after 20 idle minutes.

To start the backend without connecting, turn the automatic connection off. You can still press **Connect** in the status box later.

```powershell
$env:KAGGLE_AUTO_CONNECT="0"; uvicorn main:app --reload   # Windows (PowerShell)
```

```bash
KAGGLE_AUTO_CONNECT=0 uvicorn main:app --reload           # macOS / Linux
```

**API**

| Endpoint | What it does | Model |
|---|---|---|
| `GET /api/kaggle/status` | Current step, progress and log | – |
| `POST /api/kaggle/connect` | Connect to Kaggle | – |
| `POST /api/kaggle/stop` | End the Kaggle session | – |
| `POST /api/images/generate` | Generate a picture from text | SDXL-Turbo |
| `POST /api/images/from-sketch` | Generate a picture from a sketch and text | SDXL-Turbo |
| `POST /api/images/split` | Split a picture into layers | Qwen-Image-2.1 |
| `POST /api/layers/edit` | Edit one layer with text | Qwen-Image-2.1 |

The image endpoints return `503` until the connection reaches 100%. Try them at http://localhost:8000/docs.

**Troubleshooting**

| Message | What to do |
|---|---|
| `no Kaggle credentials` | Save your token as described above, then restart the backend |
| `Backend offline` | Start the backend (step 3) |
| Stays on `starting` for more than 25 minutes, or `failed` | Open your notebook `profile-studio-serve` at https://www.kaggle.com/code and read its log |

## Project structure

```
ttrpg-layered-scenes/
├── frontend/          React + TypeScript + Vite (layer canvas, UI)
│   └── src/
├── backend/           FastAPI (Kaggle connection, model APIs)
│   ├── main.py
│   ├── kaggle_connection.py   Connects to the Kaggle GPU session
│   ├── model_api.py           Generate, split and edit images
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── prototype/         Gradio prototype and the Kaggle launcher the backend reuses
├── .gitignore
└── README.md
```

