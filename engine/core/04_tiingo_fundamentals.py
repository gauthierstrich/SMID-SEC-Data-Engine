import os
import requests
import pandas as pd
import time
from dotenv import load_dotenv

# Load configuration
load_dotenv()
API_KEY = os.getenv("TIINGO_API_KEY")

# Dynamic Path Resolution (Works on Mac/Linux)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
REGISTRY_PATH = os.path.join(BASE_DIR, "engine/registry/master_tracker.csv")

# Storage for Fundamentals
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/Volumes/LaCie/SMID-SEC Data Engine/storage")
OUTPUT_DIR = os.path.join(LACIE_STORAGE, "bronze/fundamentals/tiingo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def vacuum_fundamentals():
    print("📈 Starting Tiingo Fundamentals Vacuum (Phase 4)...")
    
    if not os.path.exists(REGISTRY_PATH):
        print(f"❌ Error: Registry not found at {REGISTRY_PATH}")
        return

    df = pd.read_csv(REGISTRY_PATH)
    
    # Initialize status column if it doesn't exist
    if 'status_fundamentals_tiingo' not in df.columns:
        df['status_fundamentals_tiingo'] = 'pending'

    # Filter for tickers to process (Common stocks, USD, not already success)
    # Note: We process both active and de-listed stocks for "Survivorship Bias" coverage
    to_process = df[df['status_fundamentals_tiingo'] != 'success'].index.tolist()
    total = len(to_process)
    
    print(f"📦 Found {total} tickers to process for fundamentals.")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {API_KEY}'
    }

    for i, idx in enumerate(to_process):
        ticker = str(df.at[idx, 'ticker'])
        file_path = os.path.join(OUTPUT_DIR, f"{ticker}.json")
        
        print(f"🔍 [{i+1}/{total}] Fetching fundamentals for {ticker}...")
        
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker}/statements"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Save JSON to LaCie
                    with open(file_path, 'w') as f:
                        import json
                        json.dump(data, f)
                    
                    df.at[idx, 'status_fundamentals_tiingo'] = 'success'
                else:
                    print(f"⚠️ No statements found for {ticker}")
                    df.at[idx, 'status_fundamentals_tiingo'] = 'failed_empty'
                    
            elif response.status_code == 404:
                print(f"❌ Ticker {ticker} not found in Fundamentals API.")
                df.at[idx, 'status_fundamentals_tiingo'] = 'failed_404'
                
            elif response.status_code == 429:
                print("\n🛑 Rate limit reached. Sleeping 60s...")
                time.sleep(60)
                continue # Retry next iteration
                
            else:
                print(f"⚠️ Error {response.status_code} for {ticker}")
                df.at[idx, 'status_fundamentals_tiingo'] = f'failed_{response.status_code}'

        except Exception as e:
            print(f"❌ Exception for {ticker}: {e}")
            df.at[idx, 'status_fundamentals_tiingo'] = f'error: {str(e)}'

        # Checkpoint every 50 tickers
        if i % 50 == 0:
            df.to_csv(REGISTRY_PATH, index=False)

    # Final Save
    df.to_csv(REGISTRY_PATH, index=False)
    print(f"\n✅ Phase 4 Complete. Registry updated.")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Error: TIINGO_API_KEY not found in .env")
    else:
        vacuum_fundamentals()
