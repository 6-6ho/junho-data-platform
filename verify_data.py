import websocket
import json
import ssl
import requests
import time
import threading

# 1. Verify REST API (Public Klines) - No Key Needed
def check_rest_api():
    print("\n[Check 1] Binance Futures REST API (Klines)...")
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"[SUCCESS] Received {len(data)} candles.")
        print(f"Sample Candle: {data[0]}")
    except Exception as e:
        print(f"[FAILED] {e}")

# 2. Verify WebSocket (Realtime Ticker) - No Key Needed
def check_wss():
    print("\n[Check 2] Binance Futures WebSocket (All Tickers)...")
    url = "wss://fstream.binance.com/stream?streams=!ticker@arr"
    
    def on_message(ws, message):
        data = json.loads(message)
        if "data" in data:
            tickers = data["data"]
            print(f"[SUCCESS] Received batch of {len(tickers)} tickers.")
            print(f"Sample Ticker: {tickers[0]['s']} Price: {tickers[0]['c']}")
            ws.close() # Stop after one message
    
    def on_error(ws, error):
        print(f"[ERROR] WebSocket Error: {error}")
        
    ws = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == "__main__":
    print("=== Verifying Real Data Connection (No API Key Required) ===")
    check_rest_api()
    check_wss()
