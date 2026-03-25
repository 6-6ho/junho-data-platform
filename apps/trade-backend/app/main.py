from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import data, klines, favorites, analysis, smc, system, theme, settings, screener, listing, whale, agent
from .auth import auth_router

app = FastAPI(title="Trade Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(data.router)
app.include_router(klines.router)
app.include_router(favorites.router)
app.include_router(analysis.router)
app.include_router(smc.router)
app.include_router(system.router)
app.include_router(theme.router)
app.include_router(settings.router)
app.include_router(screener.router)
app.include_router(listing.router)
app.include_router(whale.router)
app.include_router(agent.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "trade-backend"}

@app.get("/api/system/status")
async def system_status():
    from sqlalchemy import text
    from app.database import SessionLocal

    status = "OPERATIONAL"
    pipeline_lag = "N/A"
    active_services = 0

    try:
        db = SessionLocal()
        # movers_latest 최신 이벤트로 파이프라인 lag 계산
        row = db.execute(text(
            "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(event_time)))::int FROM movers_latest"
        )).scalar()
        db.close()

        if row is not None:
            pipeline_lag = f"{row}s" if row < 120 else f"{row // 60}m"
            if row > 300:
                status = "DEGRADED"
        else:
            status = "DEGRADED"

        active_services = 21  # laptop compose 서비스 수
    except Exception:
        status = "DEGRADED"

    return {
        "status": status,
        "pipeline_lag": pipeline_lag,
        "active_services": active_services,
    }
