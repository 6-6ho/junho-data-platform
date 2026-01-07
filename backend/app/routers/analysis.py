from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime
from cachetools import TTLCache

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Cache for all-alts average (15 min TTL)
alts_avg_cache = TTLCache(maxsize=1, ttl=900)

@router.get("/oi/{symbol}")
async def get_open_interest(symbol: str):
    async with httpx.AsyncClient() as client:
        try:
            url_curr = "https://fapi.binance.com/fapi/v1/openInterest"
            resp_curr = await client.get(url_curr, params={"symbol": symbol})
            resp_curr.raise_for_status()
            curr_data = resp_curr.json()
            
            url_hist = "https://fapi.binance.com/futures/data/openInterestHist"
            params_hist = {"symbol": symbol, "period": "1d", "limit": 30}
            resp_hist = await client.get(url_hist, params=params_hist)
            hist_data = resp_hist.json() if resp_hist.status_code == 200 else []

            return {
                "symbol": symbol,
                "current_oi": float(curr_data.get("openInterest", 0)),
                "current_oi_value": float(curr_data.get("openInterestValue", 0)),
                "history": hist_data
            }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="Failed to fetch OI")

async def get_alts_average():
    """Calculate average 24h change for all Binance Futures USDT pairs."""
    if "avg" in alts_avg_cache:
        return alts_avg_cache["avg"]
    
    async with httpx.AsyncClient() as client:
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            resp = await client.get(url)
            resp.raise_for_status()
            tickers = resp.json()
            
            usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT") and t["symbol"] != "BTCUSDT"]
            if not usdt_pairs:
                return 0.0
            
            avg = sum(float(t.get("priceChangePercent", 0)) for t in usdt_pairs) / len(usdt_pairs)
            alts_avg_cache["avg"] = avg
            return avg
        except:
            return 0.0

@router.get("/info/{symbol}")
async def get_symbol_info(symbol: str):
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            url_kline = "https://fapi.binance.com/fapi/v1/klines"
            url_ticker = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            
            resp_listing = await client.get(url_kline, params={"symbol": symbol, "interval": "1M", "startTime": 0, "limit": 1})
            resp_symbol = await client.get(url_ticker, params={"symbol": symbol})
            resp_btc = await client.get(url_ticker, params={"symbol": "BTCUSDT"})
            
            listing_date = None
            days_since = 0
            if resp_listing.status_code == 200:
                klines = resp_listing.json()
                if klines:
                    ts = klines[0][0]
                    listing_date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    days_since = (datetime.now() - datetime.fromtimestamp(ts / 1000)).days
            
            symbol_change = float(resp_symbol.json().get("priceChangePercent", 0)) if resp_symbol.status_code == 200 else 0
            btc_change = float(resp_btc.json().get("priceChangePercent", 0)) if resp_btc.status_code == 200 else 0
            alts_avg = await get_alts_average()
            
            # CoinGecko for supply (best effort)
            circulating = None
            total = None
            try:
                # Map Binance symbol to CoinGecko ID (simple approach: lowercase base)
                base = symbol.replace("USDT", "").lower()
                cg_url = f"https://api.coingecko.com/api/v3/coins/{base}"
                cg_resp = await client.get(cg_url)
                if cg_resp.status_code == 200:
                    cg_data = cg_resp.json()
                    circulating = cg_data.get("market_data", {}).get("circulating_supply")
                    total = cg_data.get("market_data", {}).get("total_supply")
            except:
                pass  # CoinGecko is best-effort
            
            unlock_pct = None
            if circulating and total and total > 0:
                unlock_pct = (circulating / total) * 100

            return {
                "symbol": symbol,
                "listing_date": listing_date,
                "days_since_listing": days_since,
                "price_change_percent": symbol_change,
                "btc_change_percent": btc_change,
                "alts_avg_percent": alts_avg,
                "relative_strength_vs_btc": symbol_change - btc_change,
                "relative_strength_vs_alts": symbol_change - alts_avg,
                "circulating_supply": circulating,
                "total_supply": total,
                "unlock_percent": unlock_pct
            }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="Failed to fetch Symbol Info")
