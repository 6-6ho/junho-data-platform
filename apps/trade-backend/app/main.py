from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import data, klines, favorites, analysis, smc, system, theme

app = FastAPI(title="Trade Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(klines.router)
app.include_router(favorites.router)
app.include_router(analysis.router)
app.include_router(smc.router)
app.include_router(system.router)
app.include_router(theme.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "trade-backend"}

@app.get("/api/system/status")
async def system_status():
    import httpx
    import os
    
    status = "OPERATIONAL"
    active_workers = 0
    pipeline_lag = "N/A"
    
    # Spark Master API (Default to env or internal hostname)
    spark_api = os.getenv("SPARK_MASTER_API", "http://spark-master:8080")
    
    try:
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=True) as client:
            spark_resp = await client.get(f"{spark_api}/json/")
            if spark_resp.status_code == 200:
                data = spark_resp.json()
                active_workers = data.get("aliveworkers", 0)
                # 활성 앱 수로 lag 근사치 계산 (앱이 많을수록 바쁨)
                active_apps = len(data.get("activeapps", []))
                pipeline_lag = f"{0.1 + active_apps * 0.1:.2f}s"
    except Exception:
        status = "DEGRADED"
    
    return {
        "status": status,
        "pipeline_lag": pipeline_lag,
        "active_workers": active_workers,
    }
