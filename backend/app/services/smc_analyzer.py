import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import httpx

class SMCAnalyzer:
    def __init__(self):
        self.base_url = "https://fapi.binance.com/fapi/v1"

    async def fetch_klines(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """Fetch OHLCV data from Binance Futures and return as DataFrame."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit}
            )
            data = resp.json()
            
            # Binance response: [time, open, high, low, close, volume, ...]
            df = pd.DataFrame(data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", 
                "close_time", "quote_asset_volume", "trades", 
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])
            
            # Convert types
            numeric_cols = ["open", "high", "low", "close", "volume"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            
            return df

    def _get_swing_points(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """Identify Swing Highs and Swing Lows."""
        df = df.copy()
        
        # Local Max/Min within window (left and right)
        # Shift approach: Check if current is higher than +/- window candles
        # Note: This is a simplified "Rolling" approach for performance.
        # Strict definition: High[i] > High[i-k]...High[i+k]
        
        # We generally only know a swing point "after" 'window' candles have passed.
        # But for visualization we plot it at 'i'.
        
        # Vectorized implementation for basic pivots
        # Note: This is a simplistic implementation. For production, scipy.signal.argrelextrema is better but requires scipy.
        # Here we use rolling max/min.
        
        df['is_swing_high'] = False
        df['is_swing_low'] = False
        
        # Check left and right neighbors (Loop is slow, but robust for definition)
        # Using shift for vectorization
        # A simple fractal structure: 2 candles left, 2 candles right (window=2)
        
        # High detection
        period = 2 * window + 1
        df['max_roll'] = df['high'].rolling(window=period, center=True).max()
        df['min_roll'] = df['low'].rolling(window=period, center=True).min()
        
        # Identify peaks
        mask_high = (df['high'] == df['max_roll'])
        mask_low = (df['low'] == df['min_roll'])
        
        df.loc[mask_high, 'is_swing_high'] = True
        df.loc[mask_low, 'is_swing_low'] = True
        
        # Clean up consecutive highs/lows (keep highest/lowest) if needed
        # For now, simplistic approach is fine.
        
        return df

    def detect_structure(self, df: pd.DataFrame) -> Dict:
        """Detect BOS (Break of Structure) and CHoCH."""
        # Need logic:
        # 1. Trace Swing Points.
        # 2. If Price breaks previous Swing High -> Bullish BOS.
        # 3. If Price breaks previous Swing Low -> Bearish BOS.
        # CHoCH is the "first" break after a trend change.
        
        structure_events = []
        trend = "neutral" # bullish, bearish
        
        # Identify Swings first
        df_swings = self._get_swing_points(df, window=3) # Fractal length 3 (Bill Williams is 2, stick to 3 for cleaner chart)
        
        last_swing_high = None
        last_swing_low = None
        
        swings = []
        for i, row in df_swings.iterrows():
            if row['is_swing_high']:
                swings.append({
                    'type': 'high', 
                    'price': float(row['high']), 
                    'index': i, 
                    'time': row['timestamp'].isoformat()
                })
            if row['is_swing_low']:
                swings.append({
                    'type': 'low', 
                    'price': float(row['low']), 
                    'index': i, 
                    'time': row['timestamp'].isoformat()
                })
                
        # Return detected swing points for visualization
        return {
            "swings": swings
        }

    def detect_fvg(self, df: pd.DataFrame) -> List[Dict]:
        """Detect Fair Value Gaps (Bullish & Bearish)."""
        fvgs = []
        
        high = df['high'].values
        low = df['low'].values
        times = df['timestamp'] # Series
        
        for i in range(2, len(df)):
            # Bullish FVG
            if low[i] > high[i-2]:
                gap_size = low[i] - high[i-2]
                if gap_size > 0:
                    fvgs.append({
                        "type": "bullish",
                        "top": float(low[i]),
                        "bottom": float(high[i-2]),
                        "start_time": times[i-2].isoformat(),
                        "end_time": times[i].isoformat()
                    })
            
            # Bearish FVG
            if high[i] < low[i-2]:
                gap_size = low[i-2] - high[i]
                if gap_size > 0:
                    fvgs.append({
                        "type": "bearish",
                        "top": float(low[i-2]),
                        "bottom": float(high[i]),
                        "start_time": times[i-2].isoformat(),
                        "end_time": times[i].isoformat()
                    })
                    
        return fvgs

    def detect_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Detect Order Blocks (simplified)."""
        obs = []
        
        open_price = df['open'].values
        close_price = df['close'].values
        high = df['high'].values
        low = df['low'].values
        times = df['timestamp']
        
        for i in range(1, len(df) - 1):
            # Bullish OB Candidate
            is_prev_red = close_price[i-1] < open_price[i-1]
            is_curr_green = close_price[i] > open_price[i]
            engulfs = close_price[i] > high[i-1]
            
            if is_prev_red and is_curr_green and engulfs:
                obs.append({
                    "type": "bullish",
                    "top": float(high[i-1]),
                    "bottom": float(low[i-1]),
                    "time": times[i-1].isoformat()
                })

            # Bearish OB Candidate
            is_prev_green = close_price[i-1] > open_price[i-1]
            is_curr_red = close_price[i] < open_price[i]
            engulfs_down = close_price[i] < low[i-1]
            
            if is_prev_green and is_curr_red and engulfs_down:
                obs.append({
                    "type": "bearish",
                    "top": float(high[i-1]),
                    "bottom": float(low[i-1]),
                    "time": times[i-1].isoformat()
                })

        return obs[-20:]

smc_service = SMCAnalyzer()
