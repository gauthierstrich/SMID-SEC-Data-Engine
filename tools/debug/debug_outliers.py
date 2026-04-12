import polars as pl
import os
from dotenv import load_dotenv

load_dotenv()
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

query = (
    pl.scan_parquet(ALPHA_MATRIX_PATH)
    .filter(
        (pl.col("p_date") == pl.date(2024, 8, 6)) & 
        (pl.col("adjClose") < 1.0)
    )
    .select(["ticker", "cik", "adjClose", "mkt_cap", "pe_ratio"])
    .sort("adjClose")
)

pl.Config.set_tbl_rows(50)
df = query.collect()

# Chercher spécifiquement si WFC ou un autre ticker ressemble à l'outlier
wfc_ghosts = df.filter(pl.col("ticker").str.contains("(?i)wfc"))
print("--- WFC Fantômes potentiels ---")
print(wfc_ghosts)

# Regardons l'entreprise exacte qui valait 0.33 le 6 aout
suspects = df.filter((pl.col("adjClose") >= 0.329) & (pl.col("adjClose") <= 0.331))
print("\n--- Entreprises valant exactement ~0.33$ le 2024-08-06 ---")
print(suspects)
