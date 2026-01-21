from fastapi import APIRouter, HTTPException, Query
from app.services.smc_analyzer import smc_service
from typing import Optional

router = APIRouter(prefix="/api/smc", tags=["smc"])

@router.get("/analysis/{symbol}")
async def get_smc_analysis(
    symbol: str, 
    interval: str = Query("1h", pattern="^(15m|1h|4h|1d)$")
):
    """
    Get full SMC analysis for a symbol.
    Returns Swing Points, Market Structure, FVGs, and Order Blocks.
    """
    try:
        # Fetch Data
        df = await smc_service.fetch_klines(symbol, interval, limit=500)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found")

        # Run Analysis
        # 1. Swings & Structure
        structure = smc_service.detect_structure(df)
        
        # 2. FVGs
        fvgs = smc_service.detect_fvg(df)
        
        # 3. Order Blocks
        obs = smc_service.detect_order_blocks(df)
        
        # Determine Current Trend based on last BOS (simplified)
        # TODO: Implement real trend logic in detect_structure
        current_trend = "neutral"
        
        return {
            "symbol": symbol,
            "interval": interval,
            "trend": current_trend,
            "swings": structure["swings"],
            "fvgs": fvgs,
            "order_blocks": obs,
            "last_price": float(df.iloc[-1]["close"])
        }

    except Exception as e:
        print(f"Error in SMC Analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
