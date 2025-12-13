from fastapi import FastAPI
from routers import user, items #ここにリソースを追加
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(user.router)
app.include_router(items.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://hackathon-frontend-gyaf3gwcp-haruhisaasadas-projects.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)