from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from games import router as games_router

app = FastAPI(title="TTRPG Layered Scene Builder API")

# Allow the Vite dev server (frontend) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games_router)


@app.get("/health")
def health():
    return {"status": "ok"}
