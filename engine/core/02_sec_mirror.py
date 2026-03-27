import os
import json
import time
import requests
import pandas as pd

# Paths
BASE_DIR = "/Users/strichgauthier/Documents/SMID-SEC Data Engine"
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
        return "Health Care", sic_desc
    if 3570 <= sic <= 3579 or 3660 <= sic <= 3679 or 7370 <= sic <= 7379:
        return "Technology", sic_desc
    if sic == 6798:
        return "Real Estate", "REIT"
        
    # General ranges
    if 100 <= sic <= 999:
        return "Consumer Staples", sic_desc
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
        return "Consumer Discretionary", "Wholesale"
    elif 5200 <= sic <= 5999:
        return "Consumer Discretionary", "Retail"
    elif 6000 <= sic <= 6799:
        return "Financials", sic_desc
    elif 7000 <= sic <= 8999:
        return "Consumer Discretionary", "Services"
    else:
        return "Other", sic_desc

def build_cik_mapping():
    with open(SEC_TICKERS_PATH, 'r') as f:
        data = json.load(f)
    
    mapping = {}
    for key, item in data.items():
        ticker = item['ticker']
        # SEC JSON generally uppercase
        mapping[ticker.upper()] = item['cik_str']
    return mapping

def mirror_metadata():
    print("🚀 Starting SEC EDGAR Mirroring Phase...")
    
    df = pd.read_csv(REGISTRY_PATH)
    
    # Ensure columns exist
    for col in ['cik', 'sector', 'industry', 'sic', 'sic_description']:
        if col not in df.columns:
            df[col] = None

    cik_mapping = build_cik_mapping()
    
    # Identify items needing metadata
    # We target 'Field not available' strings which Tiingo puts for restricted tickers
    target_string = "Field not available for free/evaluation"
    
    to_process_indices = df[
        (df['status_metadata'] != 'success') | 
        (df['sector'] == target_string) |
        (df['sector'].isna())
    ].index.tolist()
    total = len(to_process_indices)
    
    print(f"📦 {total} tickers scheduled for SEC metadata extraction.")

    headers = {
        'User-Agent': 'SMID-SEC Data Engine admin@example.com' # SEC Mandated
    }

    save_interval = 200

    for count, idx in enumerate(to_process_indices, start=1):
        try:
            ticker = str(df.at[idx, 'ticker']).upper()
            
            # 1. Resolve CIK
            cik = cik_mapping.get(ticker)
            
            # Fallback to permaTicker split if needed (e.g., BRK.A from SEC might just be BRK, etc.)
            if not cik:
                clean_ticker = ticker.split('-')[0].split('.')[0]
                cik = cik_mapping.get(clean_ticker)
                
            if not cik:
                # Maybe it's a completely delisted ghost not in the modern SEC ticker.json
                df.at[idx, 'status_metadata'] = 'failed_no_cik_mapping'
                df.at[idx, 'sector'] = 'Ghost (Unmapped)'
                df.at[idx, 'industry'] = 'Ghost (Unmapped)'
                continue
                
            df.at[idx, 'cik'] = cik
            cik_padded = str(cik).zfill(10)
            
            print(f"📡 [{count}/{total}] Fetching SEC info for: {ticker} (CIK: {cik_padded})...", end="\r")
            
            # Pacing: Limit is 10/sec. We sleep 0.15s to be totally safe (6.6 req/sec).
            time.sleep(0.15)
            
            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                
                sic = data.get('sic')
                sic_desc = data.get('sicDescription')
                
                sector, industry = classify_sic(sic, sic_desc)
                
                df.at[idx, 'sic'] = sic
                df.at[idx, 'sic_description'] = sic_desc
                df.at[idx, 'sector'] = sector
                df.at[idx, 'industry'] = industry
                df.at[idx, 'status_metadata'] = 'success'
                
            elif response.status_code == 404:
                df.at[idx, 'status_metadata'] = 'failed_404'
            elif response.status_code == 429:
                print(f"\n🛑 SEC Rate limit reached on {ticker}. Sleeping 20s...")
                time.sleep(20)
                continue
            else:
                df.at[idx, 'status_metadata'] = f'failed_{response.status_code}'

        except Exception as e:
            df.at[idx, 'status_metadata'] = f'error: {str(e)}'
        finally:
            if count % save_interval == 0:
                current_df = pd.read_csv(REGISTRY_PATH)
                cols_to_update = ['cik', 'sic', 'sic_description', 'sector', 'industry', 'status_metadata']
                current_df.update(df[cols_to_update])
                current_df.to_csv(REGISTRY_PATH, index=False)
                print(f"\n💾 Registry Checkpoint saved at {count}/{total}")

    # Final Save
    current_df = pd.read_csv(REGISTRY_PATH)
    cols_to_update = ['cik', 'sic', 'sic_description', 'sector', 'industry', 'status_metadata']
    current_df.update(df[cols_to_update])
    current_df.to_csv(REGISTRY_PATH, index=False)
    print(f"\n✅ SEC Master Mirror test complete.")

if __name__ == "__main__":
    mirror_metadata()
