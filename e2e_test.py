import requests
import time
import sys

BASE_URL = "http://localhost:8000" # Accessing backend directly to bypass Nginx for raw API check if Nginx isn't ready, or use 3000/api
# Mapping to localhost:3000/api is better to test Nginx routing too.
API_URL = "http://localhost:3000/api"

def wait_for_service(url, name, retries=60):
    print(f"\n[{name}] Checking connectivity...")
    for i in range(retries):
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                print(f"[SUCCESS] {name} is UP!")
                return True
        except Exception as e:
            print(f"\n[DEBUG] {name} Error: {e}")
        
        if 'resp' in locals() and resp.status_code != 200:
             print(f"\n[DEBUG] {name} Status: {resp.status_code}")

        sys.stdout.write(f"\rWaiting for {name}... {i+1}/{retries}")
        time.sleep(2)
    print(f"\n❌ {name} failed to start.")
    return False

def test_movers_pipeline():
    print("\n[Data Pipeline] Verifying Real-time Data Ingestion & Processing...")
    # It takes time for Spark to init and process first batch
    max_retries = 30 # 60 seconds
    for i in range(max_retries):
        try:
            resp = requests.get(f"{API_URL}/movers/latest?limit=5")
            data = resp.json()
            if len(data) > 0:
                print(f"[SUCCESS] Movers Data Detected! (Spark Job is working)")
                print(f"Sample: {data[0]['symbol']} {data[0]['status']}")
                return True
        except Exception as e:
            print(f"Debug: {e}")
        
        sys.stdout.write(f"\rWaiting for Spark Pipeline... {i+1}/{max_retries}")
        time.sleep(2)
    
    print("\n[FAILED] Pipeline Timed Out. Spark or Ingest might be failing.")
    return False

def test_trendline_crud():
    print("\n[Backend] Testing Trendline CRUD...")
    # 1. Create
    payload = {
        "symbol": "BTCUSDT",
        "t1_ms": int(time.time()*1000),
        "p1": 50000.0,
        "t2_ms": int(time.time()*1000) + 3600000,
        "p2": 55000.0,
        "basis": "close",
        "mode": "both",
        "enabled": True
    }
    try:
        resp = requests.post(f"{API_URL}/trendlines", json=payload)
        resp.raise_for_status()
        created = resp.json()
        line_id = created["line_id"]
        print("[SUCCESS] Created Trendline")

        # 2. Get
        resp = requests.get(f"{API_URL}/trendlines?symbol=BTCUSDT")
        items = resp.json()
        if any(x["line_id"] == line_id for x in items):
            print("[SUCCESS] Checked Trendline persistence")
        else:
            print("[FAILED] Fetched list missing created item")
            return

        # 3. Delete
        requests.delete(f"{API_URL}/trendlines/{line_id}").raise_for_status()
        print("[SUCCESS] Deleted Trendline")
        
    except Exception as e:
        print(f"[FAILED] CRUD Failed: {e}")

if __name__ == "__main__":
    print("=== E2E System Test ===")
    
    # 1. Check Frontend/Nginx
    if not wait_for_service("http://localhost:3000/", "Frontend(Nginx)"):
        sys.exit(1)

    # 2. Check Backend API through Nginx
    if not wait_for_service(f"{API_URL}/klines?symbol=BTCUSDT&interval=1m&limit=1", "Backend API"):
        sys.exit(1)
        
    # 3. Test Business Logic
    test_trendline_crud()
    
    # 4. Test Data Pipeline (Ingest -> Kafka -> Spark -> DB)
    test_movers_pipeline()
