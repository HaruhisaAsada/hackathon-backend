from fastapi import FastAPI
from routers import user #ここにリソースを追加

app = FastAPI()
app.include_router(user.router)