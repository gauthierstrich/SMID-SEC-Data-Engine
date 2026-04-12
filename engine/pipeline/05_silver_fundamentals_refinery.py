import polars as pl
import os
import glob
import json
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- CONFIGURATION DYNAMIQUE ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
DEFAULT_STORAGE = os.path.join(BASE_DIR, "storage")
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", DEFAULT_STORAGE)

BRONZE_FUNDS = os.path.join(LACIE_STORAGE, "bronze/fundamentals/sec_facts")
SILVER_DIR = os.path.join(LACIE_STORAGE, "silver")
os.makedirs(SILVER_DIR, exist_ok=True)

TAG_MAP = {
    "Revenues": "revenue",
    "SalesRevenueNet": "revenue",
    "SalesRevenueGoodsNet": "revenue",
    "RevenueFromContractWithCustomerExcludingSalesTax": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "TotalRevenuesAndOtherIncome": "revenue",
    "RevenuesNetOfInterestExpense": "revenue",
    "NetIncomeLoss": "net_income",
    "NetIncomeLossAvailableToCommonStockholdersBasic": "net_income",
    "ProfitLoss": "net_income",
    "CostOfGoodsAndServicesSold": "cogs",
    "CostOfRevenue": "cogs",
    "CostOfGoodsSold": "cogs",
    "ResearchAndDevelopmentExpense": "rd_expense",
    "SellingGeneralAndAdministrativeExpense": "sga_expense",
    "OperatingExpenses": "opex",
    "OperatingIncomeLoss": "operating_income",
    "Assets": "total_assets",
    "Liabilities": "total_liabilities",
    "StockholdersEquity": "equity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "equity",
    "LiabilitiesAndStockholdersEquity": "equity_and_liab",
    "CashAndCashEquivalentsAtCarryingValue": "cash",
    "LongTermDebt": "long_term_debt",
    "LongTermDebtNoncurrent": "long_term_debt",
    "ShortTermBorrowings": "short_term_debt",
    "InventoryNet": "inventory",
    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capex",
    "CommonStockSharesOutstanding": "shares_outstanding",
    "EntityCommonStockSharesOutstanding": "shares_outstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic": "shares_outstanding",
    "WeightedAverageNumberOfDilutedSharesOutstanding": "shares_outstanding_diluted"
}

INSTANT_TAGS = {
    "total_assets", "total_liabilities", "equity", "equity_and_liab", 
    "cash", "long_term_debt", "short_term_debt", "inventory", 
    "shares_outstanding", "shares_outstanding_diluted"
}

def parse_sec_json_advanced(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    cik = str(data.get("cik", "Unknown")).zfill(10)
    us_gaap = data.get("facts", {}).get("us-gaap", {})
    all_facts = []
    
    for sec_tag, quant_name in TAG_MAP.items():
        if sec_tag in us_gaap:
            units = us_gaap[sec_tag].get("units", {})
            
            # PHASE 1: SÉCURISATION DES DEVISES (Audit RenTech)
            # On ne traite que l'USD pour les montants et 'shares' pour les actions.
            # On ignore tout le reste (CAD, EUR, pure, etc.) pour éviter la pollution des ratios.
            target_unit = None
            if quant_name in ["shares_outstanding", "shares_outstanding_diluted"]:
                target_unit = "shares"
            else:
                target_unit = "USD"
            
            if target_unit in units:
                for entry in units[target_unit]:
                    start_str = entry.get("start")
                    end_str = entry.get("end")
                    val = entry.get("val")
                    filed_str = entry.get("filed")
                    fp = entry.get("fp") # CORRECTION: get the fiscal period (Q1, Q2, FY), NOT the form type
                    
                    if not end_str or val is None or not filed_str:
                        continue
                        
                    duration_days = 0
                    if start_str:
                        try:
                            s_d = datetime.strptime(start_str, "%Y-%m-%d")
                            e_d = datetime.strptime(end_str, "%Y-%m-%d")
                            duration_days = (e_d - s_d).days
                        except:
                            pass
                            
                    is_fy = False
                    is_quarter = False
                    
                    if quant_name not in INSTANT_TAGS:
                        if duration_days > 0:
                            if 80 <= duration_days <= 105:
                                is_quarter = True
                            elif 350 <= duration_days <= 380:
                                is_fy = True
                            else:
                                continue # Ignore les periodes cumulatives (180, 270 jours)
                        else:
                            continue # Un flux doit avoir une duree
                            
                    all_facts.append({
                        "cik": cik,
                        "tag": quant_name,
                        "val": float(val), # Valeur pure
                        "raw_val": float(val), # Valeur brute
                        "end_date": end_str,
                        "filed_date": filed_str,
                        "fp": fp if fp else "Unknown",
                        "is_fy": is_fy,
                        "is_quarter": is_quarter
                    })
    return all_facts

def refine_fundamentals():
    print("🏛️ Starting Advanced SEC Refinery (Annualized Run-Rate Mode)...")
    json_files = glob.glob(os.path.join(BRONZE_FUNDS, "*.json"))
    output_path = os.path.join(SILVER_DIR, "fundamentals_master.parquet")
    if os.path.exists(output_path): os.remove(output_path)
    
    CHUNK_SIZE = 500
    writer = None

    for i in range(0, len(json_files), CHUNK_SIZE):
        chunk_files = json_files[i : i + CHUNK_SIZE]
        chunk_data = []
        for f in tqdm(chunk_files, desc=f"Block {i//CHUNK_SIZE + 1}"):
            try: chunk_data.extend(parse_sec_json_advanced(f))
            except: continue

        if chunk_data:
            df = pl.DataFrame(chunk_data)
            # Dédoublonnage: on garde 1 seule valeur par tag, par date de fin et par date de publication (Point-in-Time)
            df = df.sort(["cik", "tag", "end_date", "filed_date"]).group_by(["cik", "tag", "end_date", "filed_date", "fp", "is_fy", "is_quarter"]).first()
            
            table = df.to_arrow()
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression='zstd')
            writer.write_table(table)

    if writer: writer.close()
    print(f"✅ Fundamentals Master Built: {output_path}")

if __name__ == "__main__":
    refine_fundamentals()
