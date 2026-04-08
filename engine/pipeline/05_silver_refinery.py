import polars as pl
import os
import glob
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from dotenv import load_dotenv

# Load configuration
load_dotenv()

# Dynamic Path Resolution
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
REGISTRY_PATH = os.path.join(BASE_DIR, "engine/registry/master_tracker.csv")

# Storage Paths
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
BRONZE_PRICES = os.path.join(LACIE_STORAGE, "bronze/prices")
SILVER_DIR = os.path.join(LACIE_STORAGE, "silver")
os.makedirs(SILVER_DIR, exist_ok=True)

def scan_and_clean(f):
    basename = os.path.basename(f).replace(".csv", "")
    # Utiliser rsplit pour couper uniquement sur le dernier underscore
    parts = basename.rsplit("_", 1)
    permaTicker = parts[0]
    ticker = parts[1] if len(parts) > 1 else "Unknown"    
    # Read file
    df = pl.read_csv(f, infer_schema_length=1000)
    
    if "" in df.columns:
        df = df.drop("")
        
    schema = {
        "date": pl.String, "close": pl.Float64, "high": pl.Float64, "low": pl.Float64, "open": pl.Float64,
        "volume": pl.Float64, "adjClose": pl.Float64, "adjHigh": pl.Float64, "adjLow": pl.Float64,
        "adjOpen": pl.Float64, "adjVolume": pl.Float64, "divCash": pl.Float64, "splitFactor": pl.Float64
    }
    
    for col, dtype in schema.items():
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(dtype))
            
    return df.select(list(schema.keys())).with_columns([
        pl.lit(permaTicker).alias("permaTicker"),
        pl.lit(ticker).alias("ticker")
    ])

def refine_prices():
    print("💎 Refining Bronze Prices into Silver Parquet (Incremental Write)...")
    
    csv_files = sorted(glob.glob(os.path.join(BRONZE_PRICES, "*.csv")))
    if not csv_files:
        print("❌ No CSV files found.")
        return

    CHUNK_SIZE = 1000 
    output_path = os.path.join(SILVER_DIR, "prices_master.parquet")
    
    # Start fresh
    if os.path.exists(output_path):
        os.remove(output_path)
    
    print(f"📦 Total files: {len(csv_files)}. Writing to {output_path}...")

    writer = None

    for i in range(0, len(csv_files), CHUNK_SIZE):
        chunk_files = csv_files[i : i + CHUNK_SIZE]
        chunk_idx = i // CHUNK_SIZE
        print(f"🔄 Processing Block {chunk_idx + 1}...")
        
        chunk_dfs = []
        for f in tqdm(chunk_files, desc=f"Block {chunk_idx + 1}"):
            try:
                chunk_dfs.append(scan_and_clean(f))
            except Exception as e:
                print(f"⚠️ Error on {f}: {e}")
        
        if chunk_dfs:
            # Combine current block
            chunk_df = pl.concat(chunk_dfs)
            
            # Convert to PyArrow Table
            table = chunk_df.to_arrow()
            
            # Initialize Parquet Writer on first chunk
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression='zstd')
            
            # Write chunk to file
            writer.write_table(table)
            
            # Free memory explicitly
            del chunk_dfs, chunk_df, table

    if writer:
        writer.close()
    
    print(f"✅ Prices Master created successfully: {output_path}")

def refine_metadata():
    print("💎 Refining Metadata into Silver Parquet...")
    df = pl.read_csv(REGISTRY_PATH)
    output_path = os.path.join(SILVER_DIR, "metadata_master.parquet")
    df.write_parquet(output_path, compression="zstd")
    print(f"✅ Metadata Master created: {output_path}")

if __name__ == "__main__":
    refine_metadata()
    refine_prices()
    print("\n🏆 Silver Refinery Complete. Dataset is now unified and high-performance.")
