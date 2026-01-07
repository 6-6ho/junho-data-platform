from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import data, klines, favorites

app = FastAPI(title="Trade Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movers.router)
app.include_router(klines.router)
app.include_router(alerts.router)
app.include_router(favorites.router)
app.include_router(analysis.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "trade-helper-backend"}
