import polars as pl
import os
from dotenv import load_dotenv

load_dotenv()
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

# Analyse de NVDA autour du split (7 Juin 2024)
query = (
    pl.scan_parquet(ALPHA_MATRIX_PATH)
    .filter(
        (pl.col("ticker") == "NVDA") & 
        (pl.col("p_date") >= pl.date(2024, 6, 1)) & 
        (pl.col("p_date") <= pl.date(2024, 6, 15))
    )
    .select(["p_date", "close", "adjClose", "shares_outstanding", "mkt_cap", "pe_ratio"])
)

print(query.collect())
