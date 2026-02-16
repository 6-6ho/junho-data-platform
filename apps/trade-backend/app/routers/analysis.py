import asyncio
import logging
from fastapi import APIRouter, HTTPException
import httpx
from datetime import datetime
from cachetools import TTLCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Cache for all-alts average (15 min TTL)
alts_avg_cache = TTLCache(maxsize=1, ttl=900)

# Cache for USD/KRW rate (1 hour TTL)
usd_krw_cache = TTLCache(maxsize=1, ttl=3600)

# Cache for market cap (1 hour TTL)
market_cap_cache = TTLCache(maxsize=100, ttl=3600)

# CoinGecko ID mapping
MAJOR_COIN_IDS = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
    "xrp": "ripple", "doge": "dogecoin", "ada": "cardano",
    "bnb": "binancecoin", "dot": "polkadot", "trx": "tron",
    "link": "chainlink", "matic": "matic-network", "ltc": "litecoin",
    "bch": "bitcoin-cash", "uni": "uniswap", "xlm": "stellar",
    "etc": "ethereum-classic"
}


async def get_usd_krw_rate():
    """Get USD to KRW exchange rate."""
    if "rate" in usd_krw_cache:
        return usd_krw_cache["rate"]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                rate = data.get("rates", {}).get("KRW", 1350)
                usd_krw_cache["rate"] = rate
                return rate
        except Exception as e:
            logger.warning(f"Failed to fetch USD/KRW rate: {e}")
    return 1350


async def get_alts_average(client: httpx.AsyncClient = None):
    """Calculate average 24h change for all Binance Futures USDT pairs."""
    if "avg" in alts_avg_cache:
        return alts_avg_cache["avg"]
    
    should_close = False
    if client is None:
        client = httpx.AsyncClient()
        should_close = True

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
    except Exception as e:
        logger.warning(f"Failed to fetch alts average: {e}")
        return 0.0
    finally:
        if should_close:
            await client.aclose()


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


@router.get("/info/{symbol}")
async def get_symbol_info(symbol: str):
    """Get comprehensive symbol info with parallel API calls."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            url_kline = "https://fapi.binance.com/fapi/v1/klines"
            url_ticker = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            
            # === PARALLEL: Core Binance API calls ===
            resp_listing, resp_symbol, resp_btc = await asyncio.gather(
                client.get(url_kline, params={"symbol": symbol, "interval": "1M", "startTime": 0, "limit": 1}),
                client.get(url_ticker, params={"symbol": symbol}),
                client.get(url_ticker, params={"symbol": "BTCUSDT"}),
            )
            
            # Parse listing date
            listing_date = None
            days_since = 0
            if resp_listing.status_code == 200:
                klines = resp_listing.json()
                if klines:
                    ts = klines[0][0]
                    listing_date = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    days_since = (datetime.now() - datetime.fromtimestamp(ts / 1000)).days
            
            symbol_data = resp_symbol.json() if resp_symbol.status_code == 200 else {}
            symbol_change = float(symbol_data.get("priceChangePercent", 0))
            last_price = float(symbol_data.get("lastPrice", 0))
            volume_24h_usd = float(symbol_data.get("quoteVolume", 0))
            
            btc_change = float(resp_btc.json().get("priceChangePercent", 0)) if resp_btc.status_code == 200 else 0
            
            # === PARALLEL: Secondary API calls (all best-effort) ===
            alts_task = get_alts_average(client)
            spot_task = client.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol})
            oi_task = client.get("https://fapi.binance.com/fapi/v1/openInterest", params={"symbol": symbol})
            ls_task = client.get("https://fapi.binance.com/fapi/v1/topLongShortAccountRatio",
                                params={"symbol": symbol, "period": "5m", "limit": 1})
            
            # CoinGecko (check cache first)
            base = symbol.replace("USDT", "").lower()
            cg_id = MAJOR_COIN_IDS.get(base, base)
            
            cg_task = None
            if cg_id not in market_cap_cache:
                cg_task = client.get(f"https://api.coingecko.com/api/v3/coins/{cg_id}")
            
            # Gather all secondary calls
            tasks = [alts_task, spot_task, oi_task, ls_task]
            if cg_task:
                tasks.append(cg_task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Parse results
            alts_avg = results[0] if not isinstance(results[0], Exception) else 0.0
            
            has_spot = False
            if not isinstance(results[1], Exception):
                has_spot = results[1].status_code == 200
            
            open_interest_usd = None
            if not isinstance(results[2], Exception) and results[2].status_code == 200:
                try:
                    oi_data = results[2].json()
                    open_interest_usd = float(oi_data.get("openInterest", 0)) * last_price
                except Exception as e:
                    logger.warning(f"OI parse error for {symbol}: {e}")
            
            ls_ratio = None
            if not isinstance(results[3], Exception) and results[3].status_code == 200:
                try:
                    ls_data = results[3].json()
                    if ls_data:
                        ls_ratio = float(ls_data[0].get("longShortRatio", 0))
                except Exception as e:
                    logger.warning(f"L/S ratio parse error for {symbol}: {e}")
            
            # CoinGecko data
            circulating = None
            total = None
            market_cap_usd = None
            
            if cg_id in market_cap_cache:
                cached = market_cap_cache[cg_id]
                circulating = cached.get("circulating")
                total = cached.get("total")
                market_cap_usd = cached.get("market_cap")
            elif cg_task and len(results) > 4 and not isinstance(results[4], Exception):
                try:
                    if results[4].status_code == 200:
                        cg_data = results[4].json()
                        circulating = cg_data.get("market_data", {}).get("circulating_supply")
                        total = cg_data.get("market_data", {}).get("total_supply")
                        market_cap_usd = cg_data.get("market_data", {}).get("market_cap", {}).get("usd")
                        market_cap_cache[cg_id] = {
                            "circulating": circulating, "total": total, "market_cap": market_cap_usd
                        }
                except Exception as e:
                    logger.warning(f"CoinGecko parse error for {symbol}: {e}")
            
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
    """Get daily returns for BTC and Alts average over the last 30 days."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            url_ticker = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            url_klines = "https://fapi.binance.com/fapi/v1/klines"
            
            # Parallel fetch
            resp_tickers, btc_klines = await asyncio.gather(
                client.get(url_ticker),
                client.get(url_klines, params={"symbol": "BTCUSDT", "interval": "1d", "limit": 30})
            )
            
            resp_tickers.raise_for_status()
            all_tickers = resp_tickers.json()
            btc_data = btc_klines.json() if btc_klines.status_code == 200 else []
            
            btc_returns = []
            for k in btc_data:
                open_price = float(k[1])
                close_price = float(k[4])
                daily_return = ((close_price - open_price) / open_price) * 100
                btc_returns.append({"time": k[0], "value": round(daily_return, 2)})
            
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
    """Get all available USDT trading pairs for search."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"symbol": t["symbol"], "price": t["lastPrice"], "change": float(t["priceChangePercent"])}
                    for t in data if t["symbol"].endswith("USDT")
                ]
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch symbols: {e}")
            return []
