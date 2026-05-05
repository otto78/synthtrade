from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, strategies, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="SynthTrade API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(strategies.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
