import httpx
from fastapi import APIRouter, HTTPException, Query
from cachetools import TTLCache, cached

router = APIRouter(prefix="/api/klines", tags=["klines"])

# Simple in-memory cache: TTL 10s, Max 100 items
cache = TTLCache(maxsize=100, ttl=10)

@router.get("")
async def get_klines(symbol: str, interval: str, limit: int = 1000):
    print(f"DEBUG: get_klines called for {symbol} {interval}")
    
    cache_key = f"{symbol}_{interval}_{limit}"
    if cache_key in cache:
        print(f"DEBUG: Cache hit for {cache_key}")
        return cache[cache_key]

    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"DEBUG: Fetching from Binance {url} params={params}")
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            cache[cache_key] = data
            return data
        except httpx.HTTPError as e:
            print(f"Error fetching klines: {e}") 
            raise HTTPException(status_code=502, detail=f"Binance API Error: {str(e)}")
