from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, strategies, dashboard, logs, ws, trades, eval as eval_api, pipeline, exchange
from app.scheduler.jobs import setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched = setup_scheduler()
    sched.start()
    yield
    sched.shutdown(wait=False)


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
app.include_router(logs.router)
app.include_router(ws.router)
app.include_router(trades.router)
app.include_router(eval_api.router)
app.include_router(pipeline.router)
app.include_router(exchange.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/scheduler/status")
def scheduler_status():
    from app.scheduler.jobs import scheduler
    jobs = [{"id": j.id, "next_run": str(j.next_run_time)} for j in scheduler.get_jobs()]
    return {"running": scheduler.running, "jobs": jobs}
