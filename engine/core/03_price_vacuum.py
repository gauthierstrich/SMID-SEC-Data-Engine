import os
import requests
import pandas as pd
from dotenv import load_dotenv
import time

# Load configuration
load_dotenv()
API_KEY = os.getenv("TIINGO_API_KEY")

# Paths Based on Architecture
BASE_DIR = "/Users/strichgauthier/Documents/SMID-SEC Data Engine"
REGISTRY_PATH = os.path.join(BASE_DIR, "engine/registry/master_tracker.csv")

LACIE_DIR = "/Volumes/LaCie/SMID-SEC Data Engine/storage/bronze/prices"
os.makedirs(LACIE_DIR, exist_ok=True)

def vacuum_prices():
    print("🚀 Starting Price Vacuum Phase...")
    
    if not os.path.exists(REGISTRY_PATH):
        print(f"❌ Error: Registry not found at {REGISTRY_PATH}")
        return

    df = pd.read_csv(REGISTRY_PATH)
    
    # Identify pending items - Only those that aren't already marked done or explicitly empty/failed
    to_process_indices = df[~df['status_prices'].isin(['success', 'success_empty', 'failed_404'])].index.tolist()
    
    total = len(to_process_indices)
    print(f"📦 {total} tickers scheduled for extraction (Full Run).")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {API_KEY}'
    }

    count = 0
    save_interval = 20

    for idx in to_process_indices:
        ticker = str(df.at[idx, 'ticker'])
        permaTicker = str(df.at[idx, 'permaTicker'])
        
        print(f"📡 [{count+1}/{total}] Fetching Prices for: {ticker} ({permaTicker})...", end="\r")
        
        # Pacing: Limit is 10k/hr (~2.77 req/sec). We sleep 0.4s to be safe.
        time.sleep(0.4)
        
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?startDate=1900-01-01"
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    # Convert to dataframe and save
                    price_df = pd.DataFrame(data)
                    file_name = f"{permaTicker}_{ticker}.csv"
                    file_path = os.path.join(LACIE_DIR, file_name)
                    # Use CSV for pure raw bronze standard.
                    price_df.to_csv(file_path, index=False)
                    df.at[idx, 'status_prices'] = 'success'
                else:
                    df.at[idx, 'status_prices'] = 'success_empty'

            elif response.status_code == 404:
                # Ghost ticker fallback using permaTicker format is generally not supported for daily prices
                df.at[idx, 'status_prices'] = 'failed_404'
                
            elif response.status_code == 429:
                print(f"\n🛑 Rate limit reached on {ticker}. Sleeping 60s...")
                time.sleep(60)
                continue # Retry not implemented inherently here on simple loop, but next run will catch
            else:
                df.at[idx, 'status_prices'] = f'failed_{response.status_code}'

        except Exception as e:
            df.at[idx, 'status_prices'] = f'error: {str(e)}'

        count += 1
        if count % save_interval == 0:
            current_df = pd.read_csv(REGISTRY_PATH)
            current_df.update(df[['status_prices']])
            current_df.to_csv(REGISTRY_PATH, index=False)
            print(f"\n💾 Registry Checkpoint saved at {count}/{total}")

    # Final Save
    current_df = pd.read_csv(REGISTRY_PATH)
    current_df.update(df[['status_prices']])
    current_df.to_csv(REGISTRY_PATH, index=False)
    print(f"\n✅ Vacuum test complete. Scheduled tickers processed.")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Error: TIINGO_API_KEY not found in .env")
    else:
        vacuum_prices()
