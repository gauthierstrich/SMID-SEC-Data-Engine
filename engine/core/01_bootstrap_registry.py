import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# Load configuration
load_dotenv()
API_KEY = os.getenv("TIINGO_API_KEY")

# Dynamic Path Resolution (Works on Mac/Linux)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
REGISTRY_DIR = os.path.join(BASE_DIR, "engine/registry")
LOG_DIR = os.path.join(BASE_DIR, "engine/logs")

# Storage defaults to LaCie on Mac, but can be overridden via .env for Linux
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/Volumes/LaCie/SMID-SEC Data Engine/storage")

# Create directories if they don't exist
os.makedirs(REGISTRY_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.join(LACIE_STORAGE, "bronze/metadata"), exist_ok=True)

def bootstrap_registry():
    print("🚀 Initializing Master Registry...")
    
    # Correct endpoint for full fundamental metadata
    url = "https://api.tiingo.com/tiingo/fundamentals/meta"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {API_KEY}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"📥 Fetching fundamental metadata from Tiingo...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tickers_data = response.json()
        
        df = pd.DataFrame(tickers_data)
        initial_count = len(df)
        print(f"✅ Downloaded {initial_count} raw entries.")
        
        # Add tracking columns
        df['status_metadata'] = 'pending'
        df['status_prices'] = 'pending'
        df['status_fundamentals'] = 'pending'
        df['last_update'] = None
        df['bootstrap_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Save to Master Tracker (SSD)
        master_tracker_path = os.path.join(REGISTRY_DIR, "master_tracker.csv")
        df.to_csv(master_tracker_path, index=False)
        print(f"💾 Master Tracker saved to: {master_tracker_path}")
        
        # Save a backup to LaCie
        backup_path = os.path.join(LACIE_STORAGE, "bronze/metadata/master_tracker_backup.csv")
        df.to_csv(backup_path, index=False)
        print(f"📦 Backup saved to LaCie: {backup_path}")
        
    except Exception as e:
        print(f"❌ Error during bootstrap: {e}")
        try:
            if 'response' in locals() and response.status_code == 403:
                print("💡 Hint: 403 Forbidden might mean the API key lacks Fundamentals permissions, but it worked with curl. Check User-Agent.")
        except:
            pass

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Error: TIINGO_API_KEY not found in .env")
    else:
        bootstrap_registry()
