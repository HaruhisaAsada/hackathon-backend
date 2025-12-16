from fastapi import FastAPI
from routers import user, items, purchase #ここにリソースを追加
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(user.router)
app.include_router(items.router)
app.include_router(purchase.router)  # アイテム関連のルーターを追加

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://hackathon-frontend-f1bve0ub4-haruhisaasadas-projects.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)