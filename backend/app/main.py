from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import trendlines, data, klines

app = FastAPI(title="Trade Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trendlines.router)
app.include_router(data.router)
app.include_router(klines.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "trade-helper-backend"}
