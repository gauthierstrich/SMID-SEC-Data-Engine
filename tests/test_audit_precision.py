import polars as pl
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
PRICE_PATH = os.path.join(LACIE_STORAGE, "silver/prices_master.parquet")
FUND_PATH = os.path.join(LACIE_STORAGE, "silver/fundamentals_master.parquet")

def verify_latest_shares(ticker, cik):
    print(f"\n--- Test Méthode 'Latest Shares' : {ticker.upper()} ---")
    
    prices = pl.scan_parquet(PRICE_PATH).filter(pl.col("ticker") == ticker.lower()).collect()
    prices = prices.with_columns(pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date"))
    
    funds = pl.read_parquet(FUND_PATH).filter((pl.col("cik") == cik) & (pl.col("tag") == "shares_outstanding")).sort("filed_date")
    
    latest_shares = funds.tail(1)["val"][0]
    print(f"Dernières actions connues (SEC) : {latest_shares:,.0f}")

    df = prices.with_columns([
        (pl.col("adjClose") * latest_shares).alias("mkt_cap_latest")
    ])

    dates = [date(2024, 6, 6), date(2024, 6, 7), date(2024, 6, 10), date(2024, 6, 11)]
    print(df.filter(pl.col("p_date").is_in(dates)).select(["p_date", "close", "adjClose", "mkt_cap_latest"]))

if __name__ == "__main__":
    verify_latest_shares("nvda", "0001045810")
