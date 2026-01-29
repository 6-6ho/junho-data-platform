from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime
from cachetools import TTLCache

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Cache for all-alts average (15 min TTL)
alts_avg_cache = TTLCache(maxsize=1, ttl=900)

# Cache for USD/KRW rate (1 hour TTL)
usd_krw_cache = TTLCache(maxsize=1, ttl=3600)

# Cache for market cap (1 hour TTL)
market_cap_cache = TTLCache(maxsize=100, ttl=3600)

async def get_usd_krw_rate():
    """Get USD to KRW exchange rate."""
    if "rate" in usd_krw_cache:
        return usd_krw_cache["rate"]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Using exchangerate-api (free tier)
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                rate = data.get("rates", {}).get("KRW", 1350)  # Default fallback
                usd_krw_cache["rate"] = rate
                return rate
        except:
            pass
    return 1350  # Fallback KRW rate

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
            
            # CoinGecko for supply and market cap (best effort)
            circulating = None
            total = None
            market_cap_usd = None
            try:
                # Map Binance symbol to CoinGecko ID
                base = symbol.replace("USDT", "").lower()
                
                # Manual override for major coins where ID != symbol
                # CoinGecko IDs: bitcoin, ethereum, solana, ripple, dogecoin, cardano, etc.
                MAJOR_COIN_IDS = {
                    "btc": "bitcoin",
                    "eth": "ethereum",
                    "sol": "solana",
                    "xrp": "ripple",
                    "doge": "dogecoin",
                    "ada": "cardano",
                    "bnb": "binancecoin",
                    "dot": "polkadot",
                    "trx": "tron",
                    "link": "chainlink",
                    "matic": "matic-network",
                    "ltc": "litecoin",
                    "bch": "bitcoin-cash",
                    "uni": "uniswap",
                    "xlm": "stellar",
                    "etc": "ethereum-classic"
                }
                
                cg_id = MAJOR_COIN_IDS.get(base, base)
                
                # Check cache first
                if cg_id in market_cap_cache:
                    cached = market_cap_cache[cg_id]
                    circulating = cached.get("circulating")
                    total = cached.get("total")
                    market_cap_usd = cached.get("market_cap")
                else:
                    cg_url = f"https://api.coingecko.com/api/v3/coins/{cg_id}"
                    cg_resp = await client.get(cg_url)
                    if cg_resp.status_code == 200:
                        cg_data = cg_resp.json()
                        circulating = cg_data.get("market_data", {}).get("circulating_supply")
                        total = cg_data.get("market_data", {}).get("total_supply")
                        market_cap_usd = cg_data.get("market_data", {}).get("market_cap", {}).get("usd")
                        # Cache for 1 hour
                        market_cap_cache[cg_id] = {
                            "circulating": circulating,
                            "total": total,
                            "market_cap": market_cap_usd
                        }
            except:
                pass  # CoinGecko is best-effort
            
            unlock_pct = None
            if circulating and total and total > 0:
                unlock_pct = (circulating / total) * 100
            
            # Check if spot market exists
            has_spot = False
            try:
                spot_url = "https://api.binance.com/api/v3/ticker/price"
                spot_resp = await client.get(spot_url, params={"symbol": symbol})
                has_spot = spot_resp.status_code == 200
            except:
                pass

            # Fetch Open Interest
            open_interest_usd = None
            try:
                oi_url = "https://fapi.binance.com/fapi/v1/openInterest"
                oi_resp = await client.get(oi_url, params={"symbol": symbol})
                if oi_resp.status_code == 200:
                    oi_data = oi_resp.json()
                    # Use 'openInterest' (quantity) * current price or 'openInterestValue' directly if available?
                    # The separate endpoint used: float(curr_data.get("openInterestValue", 0)) which is usually in USDT
                    # NOTE: not all symbols might return openInterestValue in basic ticker calls, but this specific endpoint does.
                    open_interest_usd = float(oi_data.get("openInterest", 0)) * float(resp_symbol.json().get("lastPrice", 0))
            except:
                pass

            # Extract 24h Volume (Quote Volume in USDT)
            volume_24h_usd = 0.0
            if resp_symbol.status_code == 200:
                volume_24h_usd = float(resp_symbol.json().get("quoteVolume", 0))

            # Fetch Long/Short Ratio (Top Traders)
            ls_ratio = None
            try:
                ls_url = "https://fapi.binance.com/fapi/v1/topLongShortAccountRatio"
                ls_resp = await client.get(ls_url, params={"symbol": symbol, "period": "5m", "limit": 1})
                if ls_resp.status_code == 200:
                    ls_data = ls_resp.json()
                    if ls_data:
                        ls_ratio = float(ls_data[0].get("longShortRatio", 0))
            except:
                pass

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
                "unlock_percent": unlock_pct,
                "market_cap_usd": market_cap_usd,
                "has_spot_market": has_spot,
                "open_interest_usd": open_interest_usd,
                "volume_24h_usd": volume_24h_usd,
                "long_short_ratio": ls_ratio
            }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="Failed to fetch Symbol Info")

@router.get("/exchange-rate")
async def get_exchange_rate():
    """Get USD to KRW exchange rate (cached for 1 hour)."""
    rate = await get_usd_krw_rate()
    return {"usd_krw": rate}

@router.get("/market-overview")
async def get_market_overview():
    """
    Get daily returns for BTC and Alts average over the last 30 days.
    Uses klines to calculate daily % change.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            url_ticker = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            url_klines = "https://fapi.binance.com/fapi/v1/klines"
            
            # Get all tickers for alts average calculation
            resp_tickers = await client.get(url_ticker)
            resp_tickers.raise_for_status()
            all_tickers = resp_tickers.json()
            
            # Get BTC klines for historical data (30 days)
            btc_klines = await client.get(url_klines, params={
                "symbol": "BTCUSDT",
                "interval": "1d",
                "limit": 30
            })
            btc_data = btc_klines.json() if btc_klines.status_code == 200 else []
            
            # Calculate BTC daily returns
            btc_returns = []
            for k in btc_data:
                open_price = float(k[1])
                close_price = float(k[4])
                daily_return = ((close_price - open_price) / open_price) * 100
                btc_returns.append({
                    "time": k[0],
                    "value": round(daily_return, 2)
                })
            
            # Calculate current alts average
            usdt_pairs = [t for t in all_tickers if t["symbol"].endswith("USDT") and t["symbol"] != "BTCUSDT"]
            current_alts_avg = sum(float(t.get("priceChangePercent", 0)) for t in usdt_pairs) / len(usdt_pairs) if usdt_pairs else 0
            current_btc = float(next((t for t in all_tickers if t["symbol"] == "BTCUSDT"), {}).get("priceChangePercent", 0))
            
            return {
                "btc_returns": btc_returns,
                "current_btc_24h": round(current_btc, 2),
                "current_alts_avg_24h": round(current_alts_avg, 2),
                "alts_count": len(usdt_pairs)
            }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail="Failed to fetch market overview")

@router.get("/symbols")
async def get_all_symbols():
    """Get all available USDT trading pairs for search (with 24h change)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                # Filter for USDT pairs
                return [
                    {
                        "symbol": t["symbol"], 
                        "price": t["lastPrice"],
                        "change": float(t["priceChangePercent"])
                    }
                    for t in data 
                    if t["symbol"].endswith("USDT")
                ]
            return []
        except:
            return []
