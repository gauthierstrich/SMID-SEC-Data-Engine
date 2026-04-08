import polars as pl
import os
import glob
import json
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from dotenv import load_dotenv

# Load configuration
load_dotenv()

# Dynamic Path Resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

# Storage Paths
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
BRONZE_FUNDS = os.path.join(LACIE_STORAGE, "bronze/fundamentals/sec_facts")
SILVER_DIR = os.path.join(LACIE_STORAGE, "silver")
os.makedirs(SILVER_DIR, exist_ok=True)

# --- MAPPING TAXONOMIQUE ÉLARGI (Synonymes SEC -> Noms Quant Propres) ---
TAG_MAP = {
    # Income Statement
    "Revenues": "revenue",
    "SalesRevenueNet": "revenue",
    "SalesRevenueGoodsNet": "revenue",
    "RevenueFromContractWithCustomerExcludingSalesTax": "revenue",
    "CostOfGoodsAndServicesSold": "cogs",
    "CostOfRevenue": "cogs",
    "NetIncomeLoss": "net_income",
    "NetIncomeLossAvailableToCommonStockholdersBasic": "net_income",
    "OperatingIncomeLoss": "operating_income",
    "ResearchAndDevelopmentExpense": "rd_expense",
    "SellingGeneralAndAdministrativeExpense": "sga_expense",
    "DepreciationDepletionAndAmortization": "da_expense",
    "EarningsPerShareBasic": "eps_basic",
    "EarningsPerShareDiluted": "eps_diluted",
    
    # Balance Sheet
    "Assets": "total_assets",
    "Liabilities": "total_liabilities",
    "StockholdersEquity": "equity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "equity",
    "LiabilitiesAndStockholdersEquity": "equity_and_liab",
    "CashAndCashEquivalentsAtCarryingValue": "cash",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": "cash",
    "LongTermDebt": "long_term_debt",
    "LongTermDebtNoncurrent": "long_term_debt",
    "ShortTermBorrowings": "short_term_debt",
    "InventoryNet": "inventory",
    
    # Cash Flow
    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capex",
    
    # Capitalization
    "CommonStockSharesOutstanding": "shares_outstanding",
    "EntityCommonStockSharesOutstanding": "shares_outstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic": "shares_outstanding",
    "WeightedAverageNumberOfDilutedSharesOutstanding": "shares_outstanding_diluted"
}

def parse_sec_json(file_path):
    """Extrait les données Point-in-Time d'un JSON SEC Fact."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    ticker = data.get("entityName", "Unknown")
    cik = data.get("cik", "Unknown")
    
    all_facts = []
    us_gaap = data.get("facts", {}).get("us-gaap", {})
    
    # On ne boucle que sur les tags qui nous intéressent (vitesse ++)
    for sec_tag, quant_name in TAG_MAP.items():
        if sec_tag in us_gaap:
            # On cherche l'unité USD (ou shares pour les actions)
            units = us_gaap[sec_tag].get("units", {})
            currency = "USD" if "USD" in units else "shares" if "shares" in units else None
            
            if currency and currency in units:
                entries = units[currency]
                for entry in entries:
                    # Extraction Point-in-Time (PIT)
                    all_facts.append({
                        "cik": cik,
                        "tag": quant_name,
                        "value": float(entry.get("val")),
                        "end_date": entry.get("end"), # Date comptable
                        "filed_date": entry.get("filed"), # DATE DE PUBLICATION REELLE (No Cheating)
                        "form": entry.get("form"), # 10-K ou 10-Q
                        "fp": entry.get("fp") # Trimestre (Q1, Q2, etc)
                    })
    
    return all_facts

def refine_fundamentals():
    print("🏛️ Refining Bronze SEC JSONs into Silver Parquet (Quant Ready)...")
    
    json_files = glob.glob(os.path.join(BRONZE_FUNDS, "*.json"))
    if not json_files:
        print("❌ No SEC JSON files found.")
        return

    output_path = os.path.join(SILVER_DIR, "fundamentals_master.parquet")
    if os.path.exists(output_path):
        os.remove(output_path)
    
    CHUNK_SIZE = 500 # On traite 500 entreprises par bloc (JSON est lourd en CPU)
    writer = None
    
    print(f"📦 Found {len(json_files)} archives. Processing...")

    for i in range(0, len(json_files), CHUNK_SIZE):
        chunk_files = json_files[i : i + CHUNK_SIZE]
        chunk_idx = i // CHUNK_SIZE
        print(f"🔄 Processing Block {chunk_idx + 1}...")
        
        chunk_data = []
        for f in tqdm(chunk_files, desc=f"Block {chunk_idx + 1}"):
            try:
                data = parse_sec_json(f)
                chunk_data.extend(data)
            except Exception as e:
                pass # Certains JSON peuvent être malformés, on ignore.

        if chunk_data:
            # Conversion en Polars DataFrame
            df = pl.DataFrame(chunk_data)
            
            # Nettoyage rapide (Types et Tri)
            df = df.with_columns([
                pl.col("cik").cast(pl.String),
                pl.col("end_date").cast(pl.String),
                pl.col("filed_date").cast(pl.String),
                pl.col("value").cast(pl.Float64)
            ])
            
            # Conversion en PyArrow pour écriture incrémentale
            table = df.to_arrow()
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression='zstd')
            
            writer.write_table(table)
            del chunk_data, df, table # Free memory

    if writer:
        writer.close()
    
    print(f"✅ Fundamentals Master created: {output_path}")

if __name__ == "__main__":
    refine_fundamentals()
    print("\n🏆 Fundamentals Refinery Complete. Quantitative data is ready for backtesting.")
