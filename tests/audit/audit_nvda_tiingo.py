import requests
import polars as pl
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("TIINGO_API_KEY")
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
FUND_PATH = os.path.join(LACIE_STORAGE, "silver/fundamentals_master.parquet")

def audit_nvda_v2():
    print("📡 Testing NORMALIZED SHARES logic for NVDA...")
    url = f"https://api.tiingo.com/tiingo/daily/nvda/prices?startDate=2023-01-01&token={API_KEY}"
    response = requests.get(url)
    prices = pl.DataFrame(response.json()).with_columns([
        pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date")
    ]).sort("p_date")

    df_f = pl.read_parquet(FUND_PATH).filter(pl.col("cik") == "0001045810")
    df_f = df_f.pivot(values="val", index=["filed_date"], on="tag", aggregate_function="last")
    df_f = df_f.with_columns(pl.col("filed_date").str.to_date("%Y-%m-%d").alias("f_date")).sort("f_date")

    enriched = prices.join_asof(df_f, left_on="p_date", right_on="f_date")

    # --- FORMULE NORMALIZED SHARES ---
    # On calcule le nombre d'actions "équivalent adjClose" au moment du rapport
    enriched = enriched.with_columns([
        ((pl.col("close") * pl.col("shares_outstanding")) / pl.col("adjClose")).alias("norm_shares")
    ])
    
    # On prolonge ce nombre d'actions (il ne change que lors d'un nouveau rapport SEC)
    enriched = enriched.with_columns([
        pl.col("norm_shares").forward_fill().alias("norm_shares")
    ])

    # Market Cap = adjClose * norm_shares
    enriched = enriched.with_columns([
        (pl.col("adjClose") * pl.col("norm_shares")).alias("mkt_cap_final")
    ])

    result = enriched.filter(
        (pl.col("p_date") >= pl.date(2024, 5, 25)) & (pl.col("p_date") <= pl.date(2024, 6, 15))
    ).select(["p_date", "close", "adjClose", "shares_outstanding", "norm_shares", "mkt_cap_final"])

    print("\n📊 RÉSULTATS FORMULE NORMALIZED (NVDA SPLIT JUNE 2024):")
    print(result)

if __name__ == "__main__":
    audit_nvda_v2()
