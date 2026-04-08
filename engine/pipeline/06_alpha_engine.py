import polars as pl
import os
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv

# Load configuration
load_dotenv()

# Storage Paths
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
SILVER_DIR = os.path.join(LACIE_STORAGE, "silver")
PRICE_PATH = os.path.join(SILVER_DIR, "prices_master.parquet")
FUND_PATH = os.path.join(SILVER_DIR, "fundamentals_master.parquet")
META_PATH = os.path.join(SILVER_DIR, "metadata_master.parquet")

def normalize_cik(val):
    if val is None: return None
    try:
        return str(int(float(val)))
    except:
        return str(val)

def generate_alpha_matrix_pro():
    print("🚀 [PHASE 6] Generating Institutional Alpha Matrix...")

    # 1. Metadata & Sectors
    df_meta = pl.read_parquet(META_PATH).select(["permaTicker", "ticker", "cik", "sector", "industry"])
    df_meta = df_meta.with_columns(
        pl.col("cik").map_elements(normalize_cik, return_dtype=pl.String).alias("cik_clean")
    )
    meta_data = {row['permaTicker']: row for row in df_meta.to_dicts()}

    # 2. Pre-process Fundamentals (Pivoted)
    print("📦 Pre-processing Fundamentals...")
    df_f = pl.read_parquet(FUND_PATH)
    df_f = df_f.with_columns(pl.col("cik").cast(pl.String))
    
    df_f_pivoted = df_f.pivot(
        values="value",
        index=["cik", "filed_date"],
        on="tag",
        aggregate_function="last"
    ).with_columns(
        pl.col("filed_date").str.to_date("%Y-%m-%d").alias("f_date")
    ).sort("f_date")

    # 3. Setup Output
    output_path = os.path.join(SILVER_DIR, "alpha_matrix_pro.parquet")
    if os.path.exists(output_path):
        os.remove(output_path)

    # 4. Sequential Processing
    print("📦 Calculating Quantitative Signals (Value, Quality, Momentum, Volatility)...")
    df_p_scan = pl.scan_parquet(PRICE_PATH)
    unique_tickers = df_meta["permaTicker"].unique().to_list()
    
    writer = None
    count_success = 0

    for pt in tqdm(unique_tickers, desc="Enriching Tickers"):
        meta = meta_data.get(pt)
        if not meta: continue
        
        # Load and clean prices
        ticker_prices = df_p_scan.filter(pl.col("permaTicker") == pt).collect()
        if ticker_prices.is_empty(): continue
        
        # Data Prep & Daily Signals
        enriched = ticker_prices.with_columns([
            pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date"),
            (pl.col("close") * pl.col("volume")).alias("dollar_volume")
        ]).sort("p_date")
        
        # Price signals: Momentum & Volatility
        enriched = enriched.with_columns([
            (pl.col("close") / pl.col("close").shift(1) - 1).alias("daily_return"),
            (pl.col("close") / pl.col("close").shift(21) - 1).alias("mom_1m"),
            (pl.col("close") / pl.col("close").shift(63) - 1).alias("mom_3m"),
            (pl.col("close") / pl.col("close").shift(126) - 1).alias("mom_6m"),
            (pl.col("close") / pl.col("close").shift(252) - 1).alias("mom_12m")
        ])

        enriched = enriched.with_columns([
            pl.col("daily_return").rolling_std(window_size=30).alias("vol_30d"),
            pl.col("daily_return").rolling_std(window_size=90).alias("vol_90d"),
            pl.col("dollar_volume").rolling_mean(window_size=20).alias("adv_20d")
        ])
        
        # Match with fundamentals
        cik = meta["cik_clean"]
        if not cik or cik == "None": continue
        
        ticker_funds = df_f_pivoted.filter(pl.col("cik") == cik)
        
        if not ticker_funds.is_empty():
            # Point-in-Time Join
            enriched = enriched.join_asof(ticker_funds, left_on="p_date", right_on="f_date")
            
            if not enriched["f_date"].is_not_null().any(): continue

            # Add Sector
            sector_val = str(meta["sector"]) if meta["sector"] else "Unknown"
            industry_val = str(meta["industry"]) if meta["industry"] else "Unknown"
            
            enriched = enriched.with_columns([
                pl.lit(sector_val).alias("sector"),
                pl.lit(industry_val).alias("industry")
            ])

            # CALCULATE RATIOS (The Quant Secret Sauce)
            # Fill missing columns
            for col in ["revenue", "cogs", "net_income", "operating_income", "equity", "total_assets", "cash", "long_term_debt", "short_term_debt", "operating_cash_flow", "capex", "shares_outstanding", "da_expense", "eps_basic"]:
                if col not in enriched.columns:
                    enriched = enriched.with_columns(pl.lit(None).cast(pl.Float64).alias(col))

            enriched = enriched.with_columns([
                # Market Cap
                (pl.col("close") * pl.col("shares_outstanding")).alias("mkt_cap")
            ])

            enriched = enriched.with_columns([
                # Value
                (pl.col("mkt_cap") / pl.col("net_income").replace(0, None)).alias("pe_ratio"),
                (pl.col("close") / (pl.col("equity") / pl.col("shares_outstanding")).replace(0, None)).alias("pb_ratio"),
                ((pl.col("mkt_cap") + pl.col("long_term_debt").fill_null(0) + pl.col("short_term_debt").fill_null(0) - pl.col("cash").fill_null(0)) / (pl.col("operating_income") + pl.col("da_expense").fill_null(0)).replace(0, None)).alias("ev_ebitda"),
                ((pl.col("operating_cash_flow") - pl.col("capex").fill_null(0)) / pl.col("mkt_cap").replace(0, None)).alias("fcf_yield"),
                
                # Quality
                (pl.col("net_income") / pl.col("equity").replace(0, None)).alias("roe"),
                (pl.col("net_income") / pl.col("total_assets").replace(0, None)).alias("roa"),
                ((pl.col("revenue") - pl.col("cogs").fill_null(0)) / pl.col("revenue").replace(0, None)).alias("gross_margin"),
                ((pl.col("long_term_debt").fill_null(0) + pl.col("short_term_debt").fill_null(0)) / pl.col("equity").replace(0, None)).alias("debt_to_equity"),
                ((pl.col("net_income") - pl.col("operating_cash_flow")) / pl.col("total_assets").replace(0, None)).alias("accruals")
            ])
            
            # Final output selection
            final_cols = ["permaTicker", "ticker", "p_date", "close", "volume", "sector", "industry", 
                          "mkt_cap", "pe_ratio", "pb_ratio", "ev_ebitda", "fcf_yield", 
                          "roe", "roa", "gross_margin", "debt_to_equity", "accruals",
                          "mom_1m", "mom_3m", "mom_6m", "mom_12m", "vol_30d", "vol_90d", "adv_20d"]
            
            final_df = enriched.select([c for col in final_cols if (c := col) in enriched.columns])
            
            # Write Block
            table = final_df.to_arrow()
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression='zstd')
            writer.write_table(table)
            count_success += 1

    if writer:
        writer.close()
    print(f"\n✅ Alpha Matrix Pro created: {output_path}")
    print(f"📊 {count_success} tickers successfully enriched.")

if __name__ == "__main__":
    generate_alpha_matrix_pro()
