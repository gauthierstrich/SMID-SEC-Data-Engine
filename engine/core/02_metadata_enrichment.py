import os
import requests
import pandas as pd
from dotenv import load_dotenv
import time
import re

# Load configuration
load_dotenv()
API_KEY = os.getenv("TIINGO_API_KEY")
BASE_DIR = "/Users/strichgauthier/Documents/SMID-SEC Data Engine"
REGISTRY_PATH = os.path.join(BASE_DIR, "engine/registry/master_tracker.csv")
LOG_DIR = os.path.join(BASE_DIR, "engine/logs")

os.makedirs(LOG_DIR, exist_ok=True)

def extract_cik(url):
    """Extracts CIK from SEC Filing website URL."""
    if not isinstance(url, str):
        return None
    match = re.search(r"CIK=(\d+)", url)
    return match.group(1) if match else None

def enrich_metadata():
    print("💎 Starting Metadata Enrichment (Batch Mode)...")
    
    if not os.path.exists(REGISTRY_PATH):
        print(f"❌ Error: Registry not found at {REGISTRY_PATH}")
        return

    df = pd.read_csv(REGISTRY_PATH)
    
    # Initialize track columns if they don't exist
    for col in ['cik', 'is_us_stock', 'status_metadata']:
        if col not in df.columns:
            df[col] = None
    
    # Filtering logic: USD Only & Common Stocks (via isADR)
    df['is_us_stock'] = (df['reportingCurrency'].str.lower() == 'usd') & (df['isADR'] == False)
    
    # Identify pending items
    # We filter out items that already succeeded or failed with a 404 (to avoid infinite retries on invalid tickers)
    # But for this batch run, we target everything not 'success'
    to_process_indices = df[df['status_metadata'] != 'success'].index.tolist()
    total_to_process = len(to_process_indices)
    
    # TEST LIMIT: Set to 500 for a significant first run, or remove for full
    # to_process_indices = to_process_indices[:500]
    # total_to_process = len(to_process_indices)
    
    print(f"📦 {total_to_process} tickers to enrich.")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {API_KEY}'
    }

    batch_size = 100
    
    for i in range(0, total_to_process, batch_size):
        batch_indices = to_process_indices[i : i + batch_size]
        batch_tickers = df.loc[batch_indices, 'ticker'].tolist()
        
        # Filter out NaN tickers (shouldn't happen but safe)
        batch_tickers = [str(t) for t in batch_tickers if pd.notna(t)]
        if not batch_tickers: continue

        tickers_str = ",".join(batch_tickers)
        print(f"🔍 [{i+len(batch_indices)}/{total_to_process}] Fetching batch of {len(batch_indices)} tickers...")
        
        url = f"https://api.tiingo.com/tiingo/fundamentals/meta?tickers={tickers_str}"
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                results = response.json()
                # Create a map of ticker -> data for easy lookup
                results_map = {res['ticker'].lower(): res for res in results}
                
                for idx in batch_indices:
                    ticker = str(df.at[idx, 'ticker']).lower()
                    if ticker in results_map:
                        data = results_map[ticker]
                        
                        df.at[idx, 'sector'] = data.get('sector')
                        df.at[idx, 'industry'] = data.get('industry')
                        df.at[idx, 'sicCode'] = data.get('sicCode')
                        df.at[idx, 'sicSector'] = data.get('sicSector')
                        df.at[idx, 'sicIndustry'] = data.get('sicIndustry')
                        df.at[idx, 'location'] = data.get('location')
                        df.at[idx, 'companyWebsite'] = data.get('companyWebsite')
                        df.at[idx, 'secFilingWebsite'] = data.get('secFilingWebsite')
                        df.at[idx, 'cik'] = extract_cik(data.get('secFilingWebsite'))
                        
                        # Verify reporting currency again if missing
                        if pd.isna(df.at[idx, 'reportingCurrency']):
                            df.at[idx, 'reportingCurrency'] = data.get('reportingCurrency')
                        
                        df.at[idx, 'status_metadata'] = 'success'
                    else:
                        # Ticker not found in fundamental metadata result
                        df.at[idx, 'status_metadata'] = 'failed_not_in_fundamentals'
                
            elif response.status_code == 429:
                print("\n🛑 Rate limit reached. Sleeping 60s...")
                time.sleep(60)
                # Not retrying automatically in this batch for safety, will rerun next session
                continue 
            else:
                print(f"⚠️ Batch failed with status {response.status_code}")
                for idx in batch_indices:
                    df.at[idx, 'status_metadata'] = f'failed_{response.status_code}'

        except Exception as e:
            print(f"❌ Error during batch: {e}")
            for idx in batch_indices:
                df.at[idx, 'status_metadata'] = f'error: {str(e)}'

        # Checkpoint every batch
        df.to_csv(REGISTRY_PATH, index=False)

    print(f"\n✅ Enrichment complete. {df[df['status_metadata'] == 'success'].shape[0]} tickers total succeeded.")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Error: TIINGO_API_KEY not found in .env")
    else:
        enrich_metadata()
