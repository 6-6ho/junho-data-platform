import requests
import time

def verify_smc_api():
    url = "http://localhost:3000/api/smc/analysis/BTCUSDT?interval=1h"
    print(f"Checking {url}...")
    
    for i in range(10):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                print("Response received!")
                
                # Verify Order Blocks
                obs = data.get("order_blocks", [])
                print(f"Order Blocks found: {len(obs)}")
                
                if obs:
                    first_ob = obs[0]
                    ts = first_ob.get("time")
                    print(f"OB Timestamp: {ts} (Type: {type(ts)})")
                    
                    if isinstance(ts, int) and ts > 1000000000000:
                        print("✅ Success: OB Timestamp is valid.")
                        return True
                    else:
                        print(f"❌ Failure: OB Timestamp invalid. Got {ts}")
                        return False
                else:
                    print("⚠️ Warning: No Order Blocks detected (could be neutral market)")
                    return True
            else:
                print(f"Status: {resp.status_code}")
        except Exception as e:
            print(f"Connection failed: {e}")
        
        print("Waiting for server...")
        time.sleep(5)
    
    print("❌ Failed to connect after multiple retries.")
    return False

if __name__ == "__main__":
    verify_smc_api()
