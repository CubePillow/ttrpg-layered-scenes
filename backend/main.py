from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kaggle_connection import auto_connect as connect_kaggle
from kaggle_connection import router as kaggle_router
from model_api import router as model_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    connect_kaggle()
    yield


app = FastAPI(title="TTRPG Layered Scene Builder API", lifespan=lifespan)

# Allow the Vite dev server (frontend) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kaggle_router)
app.include_router(model_router)


@app.get("/health")
def health():
    return {"status": "ok"}
