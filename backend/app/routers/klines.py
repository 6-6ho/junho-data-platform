import httpx
from fastapi import APIRouter, HTTPException, Query
from cachetools import TTLCache, cached

router = APIRouter(prefix="/api/klines", tags=["klines"])

# Simple in-memory cache: TTL 10s, Max 100 items
cache = TTLCache(maxsize=100, ttl=10)

@router.get("")
@router.get("")
async def get_klines(symbol: str, interval: str, limit: int = 1000):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Binance API Error: {str(e)}")
