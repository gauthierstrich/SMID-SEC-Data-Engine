import os
import time
import pandas as pd
import subprocess
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "engine/registry/master_tracker.csv")
PRICE_STATUS_TMP = os.path.join(PROJECT_ROOT, "engine/registry/status_prices_tmp.csv")
SEC_STATUS_TMP = os.path.join(PROJECT_ROOT, "engine/registry/status_sec_tmp.csv")

def is_running(script_name):
    try:
        output = subprocess.check_output(["ps", "aux"])
        return script_name in output.decode()
    except:
        return False

def merge_status():
    print("🔄 Merging temporary status files into Master Registry...")
    df = pd.read_csv(REGISTRY_PATH)
    
    # Merge Prices
    if os.path.exists(PRICE_STATUS_TMP):
        try:
            p_status = pd.read_csv(PRICE_STATUS_TMP, names=['idx', 'status'])
            for _, row in p_status.iterrows():
                df.at[int(row['idx']), 'status_prices'] = row['status']
            os.remove(PRICE_STATUS_TMP)
        except Exception as e:
            print(f"⚠️ Error merging prices: {e}")

    # Merge SEC
    if os.path.exists(SEC_STATUS_TMP):
        try:
            s_status = pd.read_csv(SEC_STATUS_TMP, names=['idx', 'status'])
            for _, row in s_status.iterrows():
                df.at[int(row['idx']), 'status_fundamentals_sec'] = row['status']
            os.remove(SEC_STATUS_TMP)
        except Exception as e:
            print(f"⚠️ Error merging SEC: {e}")

    df.to_csv(REGISTRY_PATH, index=False)
    print("✅ Registry synchronized.")

def run_script(path):
    print(f"🚀 Starting {os.path.basename(path)}...")
    return subprocess.Popen(["python3", path])

def main():
    print("🎯 Orchestrator Active: Monitoring Data Engine...")
    
    while True:
        prices_active = is_running("03_price_vacuum.py")
        sec_active = is_running("04_sec_fundamentals.py")
        
        if not prices_active and not sec_active:
            print("🏁 All downloads finished. Processing results...")
            merge_status()
            
            # Vérification de l'exhaustivité (Auto-Retry)
            df = pd.read_csv(REGISTRY_PATH)
            missing_prices = df[~df['status_prices'].isin(['success', 'success_empty', 'failed_404'])].shape[0]
            # On vérifie fundamentals_sec pour la SEC
            missing_sec = df[(df['cik'].notna()) & (~df['status_fundamentals_sec'].isin(['success', 'failed_404']))].shape[0]
            
            if (missing_prices > 0 or missing_sec > 0):
                print(f"⚠️ Missing data detected ({missing_prices} prices, {missing_sec} sec). Retrying...")
                if missing_prices > 0: run_script(os.path.join(PROJECT_ROOT, "engine/pipeline/03_price_vacuum.py"))
                if missing_sec > 0: run_script(os.path.join(PROJECT_ROOT, "engine/pipeline/04_sec_fundamentals.py"))
                time.sleep(60) # Attendre que les scripts démarrent
                continue
            else:
                print("🏆 DATASET PERFECT. All stages successful.")
                break
        
        time.sleep(60) # Vérification toutes les minutes

if __name__ == "__main__":
    main()
