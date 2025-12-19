from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import user, items, purchase
from utils.pid_assigner import PIDAssigner

PID_MATCHER_PATH = os.getenv("PID_MATCHER_PATH", "utils/pid_matcher.pkl")

@asynccontextmanager
async def lifespan(app: FastAPI):
    matcher_path = Path(PID_MATCHER_PATH)
    if not matcher_path.exists():
        raise RuntimeError(f"PID matcher file not found: {matcher_path}")
    app.state.pid_assigner = PIDAssigner(str(matcher_path))
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(user.router)
app.include_router(items.router)
app.include_router(purchase.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://hackathon-frontend-2i93y6emk-haruhisaasadas-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
