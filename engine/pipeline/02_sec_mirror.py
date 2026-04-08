import os
import json
import time
import requests
import pandas as pd
from dotenv import load_dotenv

# Load configuration
load_dotenv()

# Dynamic Path Resolution (Works on Mac/Linux)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
REGISTRY_PATH = os.path.join(BASE_DIR, "engine/registry/master_tracker.csv")
SEC_TICKERS_PATH = os.path.join(BASE_DIR, "engine/registry/sec_tickers.json")

# SEC Identity mapping rules (SIC -> Sectors)
def classify_sic(sic_code, sic_desc):
    if not sic_code or pd.isna(sic_code):
        return "Unknown", "Unknown"
        
    try:
        sic = int(sic_code)
    except:
        return "Unknown", str(sic_desc)

    # Custom Tech & Health exceptions
    if 2830 <= sic <= 2836 or 8000 <= sic <= 8099:
        return "Healthcare", sic_desc
    if 3570 <= sic <= 3579 or 3660 <= sic <= 3679 or 7370 <= sic <= 7379:
        return "Technology", sic_desc
    if sic == 6798:
        return "Real Estate", "REIT"
        
    # General ranges
    if 100 <= sic <= 999:
        return "Consumer Defensive", sic_desc
    elif 1000 <= sic <= 1499:
        return "Basic Materials", sic_desc
    elif 1500 <= sic <= 1799:
        return "Industrials", "Construction"
    elif 2000 <= sic <= 3999:
        return "Industrials", "Manufacturing"
    elif 4000 <= sic <= 4899:
        return "Industrials", "Transportation & Comm"
    elif 4900 <= sic <= 4999:
        return "Utilities", sic_desc
    elif 5000 <= sic <= 5199:
        return "Consumer Cyclical", "Wholesale"
    elif 5200 <= sic <= 5999:
        return "Consumer Cyclical", "Retail"
    elif 6000 <= sic <= 6799:
        return "Financial Services", sic_desc
    elif 7000 <= sic <= 8999:
        return "Consumer Cyclical", "Services"
    else:
        return "Other", sic_desc

def mirror_metadata():
    print("🚀 Starting SEC EDGAR Mirroring Phase (Sector Extraction)...")
    
    if not os.path.exists(REGISTRY_PATH):
        print(f"❌ Error: Registry not found at {REGISTRY_PATH}")
        return

    df = pd.read_csv(REGISTRY_PATH)
    
    # Target tickers that have a CIK but no valid sector yet
    target_string = "Field not available for free/evaluation"
    to_process = df[
        (df['cik'].notna()) & 
        ((df['sector'] == target_string) | (df['sector'].isna()) | (df['sector'] == "Unknown"))
    ].index.tolist()
    
    total = len(to_process)
    print(f"📦 {total} tickers scheduled for SEC metadata extraction.")

    headers = {
        'User-Agent': 'SMID-SEC Data Engine admin@example.com' # SEC Mandated
    }

    save_interval = 200

    for count, idx in enumerate(to_process, start=1):
        try:
            ticker = str(df.at[idx, 'ticker']).upper()
            cik = str(int(df.at[idx, 'cik'])).zfill(10)
            
            print(f"📡 [{count}/{total}] Fetching SEC info for: {ticker} (CIK: {cik})...", end="\r")
            
            # Pacing: Limit is 10/sec. We sleep 0.15s to be safe.
            time.sleep(0.15)
            
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                
                sic = data.get('sic')
                sic_desc = data.get('sicDescription')
                
                sector, industry = classify_sic(sic, sic_desc)
                
                df.at[idx, 'sicCode'] = sic
                df.at[idx, 'sicIndustry'] = sic_desc
                df.at[idx, 'sector'] = sector
                df.at[idx, 'industry'] = industry
                df.at[idx, 'status_metadata'] = 'success'
                
            elif response.status_code == 404:
                df.at[idx, 'status_metadata'] = 'failed_404'
            elif response.status_code == 429:
                print(f"\n🛑 SEC Rate limit reached on {ticker}. Sleeping 30s...")
                time.sleep(30)
                continue
            else:
                df.at[idx, 'status_metadata'] = f'failed_{response.status_code}'

        except Exception as e:
            df.at[idx, 'status_metadata'] = f'error: {str(e)}'
        
        if count % save_interval == 0:
            df.to_csv(REGISTRY_PATH, index=False)
            print(f"\n💾 Registry Checkpoint saved at {count}/{total}")

    # Final Save
    df.to_csv(REGISTRY_PATH, index=False)
    print(f"\n✅ SEC Master Mirror complete. {total} sectors updated.")

if __name__ == "__main__":
    mirror_metadata()
