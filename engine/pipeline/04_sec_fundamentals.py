import os
import requests
import pandas as pd
import time
import json
from dotenv import load_dotenv

# Load configuration
load_dotenv()

# Dynamic Path Resolution (Works on Mac/Linux)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
REGISTRY_PATH = os.path.join(BASE_DIR, "engine/registry/master_tracker.csv")

# Storage for SEC Fundamentals (JSON Facts)
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
OUTPUT_DIR = os.path.join(LACIE_STORAGE, "bronze/fundamentals/sec_facts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# SEC Requirements
# IMPORTANT: SEC requires a specific User-Agent with your name/email
USER_AGENT = "SMID-SEC Data Engine (admin@example.com)" 

def vacuum_sec_fundamentals():
    print("🏛️ Starting SEC EDGAR Fundamentals Vacuum (Phase 4)...")
    
    if not os.path.exists(REGISTRY_PATH):
        print(f"❌ Error: Registry not found at {REGISTRY_PATH}")
        return

    df = pd.read_csv(REGISTRY_PATH)
    
    # Ensure CIK is available (required for SEC)
    if 'cik' not in df.columns:
        print("❌ Error: CIK column missing. Run Phase 2 (sec_mirror) first.")
        return

    # Filter for tickers to process (having CIK, not already success)
    to_process = df[
        (df['status_fundamentals'] != 'success') & 
        (df['cik'].notna())
    ].index.tolist()
    
    total = len(to_process)
    print(f"📦 {total} tickers scheduled for SEC Facts extraction.")

    headers = {
        'User-Agent': USER_AGENT,
        'Accept-Encoding': 'gzip, deflate' # SEC likes compressed transfers
    }

    # SEC Rate Limit: 10 requests per second across all tools
    # We use 0.15s delay to be safe and conservative (~6.6 req/sec)
    RATE_DELAY = 0.15 

    for i, idx in enumerate(to_process, start=1):
        ticker = str(df.at[idx, 'ticker'])
        cik = str(int(df.at[idx, 'cik'])).zfill(10) # SEC requires 10-digit padded CIK
        
        file_path = os.path.join(OUTPUT_DIR, f"{ticker}_CIK{cik}.json")
        
        # Skip if already exists on disk (Atomic Resume)
        if os.path.exists(file_path):
             df.at[idx, 'status_fundamentals'] = 'success'
             continue

        print(f"📡 [{i}/{total}] Fetching SEC Facts for {ticker} (CIK: {cik})...", end="\r")
        
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        
        try:
            time.sleep(RATE_DELAY)
            # Standard request
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                with open(file_path, 'w') as f:
                    json.dump(data, f)
                df.at[idx, 'status_fundamentals'] = 'success'
                
            elif response.status_code == 404:
                # No XBRL data for this CIK (common for very small/old companies)
                df.at[idx, 'status_fundamentals'] = 'failed_no_xbrl'
                
            elif response.status_code == 403:
                print(f"\n🛑 SEC 403 Forbidden - Check User-Agent or IP block.")
                break # Hard stop to investigate
                
            elif response.status_code == 429:
                print(f"\n⚠️ SEC Rate Limit hit for {ticker}. Pacing for 30s...")
                time.sleep(30)
                continue
                
            else:
                df.at[idx, 'status_fundamentals'] = f'failed_{response.status_code}'

        except Exception as e:
            print(f"\n❌ Exception for {ticker}: {e}")
            df.at[idx, 'status_fundamentals'] = f'error: {str(e)}'

        # Checkpoint every 200 tickers
        if i % 200 == 0:
            current_df = pd.read_csv(REGISTRY_PATH)
            # Use update to avoid overwriting concurrent changes if any
            current_df.update(df[['status_fundamentals']])
            current_df.to_csv(REGISTRY_PATH, index=False)
            print(f"\n💾 Registry Checkpoint: {i}/{total} saved.")

    # Final Save
    current_df = pd.read_csv(REGISTRY_PATH)
    current_df.update(df[['status_fundamentals']])
    current_df.to_csv(REGISTRY_PATH, index=False)
    print(f"\n✅ SEC Phase 4 Complete. Data stored in Bronze Fundamentals.")

if __name__ == "__main__":
    vacuum_sec_fundamentals()
