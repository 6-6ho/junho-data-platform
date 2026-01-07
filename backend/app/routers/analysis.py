from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

@router.get("/oi/{symbol}")
async def get_open_interest(symbol: str):
    async with httpx.AsyncClient() as client:
        try:
            url_curr = "https://fapi.binance.com/fapi/v1/openInterest"
            resp_curr = await client.get(url_curr, params={"symbol": symbol})
            resp_curr.raise_for_status()
            curr_data = resp_curr.json()
            
            url_hist = "https://fapi.binance.com/futures/data/openInterestHist"
            params_hist = {"symbol": symbol, "period": "15m", "limit": 50}
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

@router.get("/info/{symbol}")
async def get_symbol_info(symbol: str):
    async with httpx.AsyncClient() as client:
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

            return {
                "symbol": symbol,
                "listing_date": listing_date,
                "days_since_listing": days_since,
                "price_change_percent": symbol_change,
                "btc_change_percent": btc_change,
                "relative_strength": symbol_change - btc_change
            }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="Failed to fetch Symbol Info")
