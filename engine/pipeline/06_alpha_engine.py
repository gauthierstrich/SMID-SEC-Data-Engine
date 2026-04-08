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

def generate_alpha_matrix_master():
    print("🚀 [PHASE 6] Generating Master Alpha Matrix (All-Data Edition)...")

    # 1. Metadata
    df_meta = pl.read_parquet(META_PATH).select(["permaTicker", "ticker", "cik", "sector", "industry"])
    df_meta = df_meta.with_columns(
        pl.col("cik").map_elements(normalize_cik, return_dtype=pl.String).alias("cik_clean")
    )
    meta_data = {row['permaTicker']: row for row in df_meta.to_dicts()}

    # 2. Fundamentals
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
    output_path = os.path.join(SILVER_DIR, "alpha_matrix_master.parquet")
    if os.path.exists(output_path):
        os.remove(output_path)

    # 4. Sequential Ticker Processing
    print("📦 Building All-Signals Matrix (Value, Quality, Growth, Intensity, Momentum)...")
    df_p_scan = pl.scan_parquet(PRICE_PATH)
    unique_tickers = df_meta["permaTicker"].unique().to_list()
    
    writer = None
    count_success = 0

    for pt in tqdm(unique_tickers, desc="Processing Tickers"):
        meta = meta_data.get(pt)
        if not meta: continue
        
        ticker_prices = df_p_scan.filter(pl.col("permaTicker") == pt).collect()
        if ticker_prices.is_empty(): continue
        
        # Prepare Price & Liquidity Data
        enriched = ticker_prices.with_columns([
            pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date"),
            (pl.col("close") * pl.col("volume")).alias("dollar_volume")
        ]).sort("p_date")
        
        # Daily Return & Momentum
        enriched = enriched.with_columns([
            (pl.col("close") / pl.col("close").shift(1) - 1).alias("daily_return"),
            (pl.col("close") / pl.col("close").shift(21) - 1).alias("mom_1m"),
            (pl.col("close") / pl.col("close").shift(63) - 1).alias("mom_3m"),
            (pl.col("close") / pl.col("close").shift(252) - 1).alias("mom_12m")
        ])

        # Volatility & ADV
        enriched = enriched.with_columns([
            pl.col("daily_return").rolling_std(window_size=30).alias("vol_30d"),
            pl.col("daily_return").rolling_std(window_size=90).alias("vol_90d"),
            pl.col("dollar_volume").rolling_mean(window_size=20).alias("adv_20d")
        ])
        
        # Jointure As-of avec la SEC
        cik = meta["cik_clean"]
        if not cik or cik == "None": continue
        ticker_funds = df_f_pivoted.filter(pl.col("cik") == cik)
        
        if not ticker_funds.is_empty():
            enriched = enriched.join_asof(ticker_funds, left_on="p_date", right_on="f_date")
            if not enriched["f_date"].is_not_null().any(): continue

            # Remplissage des colonnes manquantes pour éviter les crashs de calcul
            needed_tags = ["revenue", "cogs", "net_income", "operating_income", "equity", "total_assets", 
                           "cash", "long_term_debt", "short_term_debt", "operating_cash_flow", 
                           "capex", "shares_outstanding", "da_expense", "rd_expense", "sga_expense"]
            for col in needed_tags:
                if col not in enriched.columns:
                    enriched = enriched.with_columns(pl.lit(None).cast(pl.Float64).alias(col))

            # --- CALCUL DES SIGNAUX ALPHA (FORMULES INSTITUTIONNELLES) ---
            # 1. Valeur (Value)
            mkt_cap = (pl.col("close") * pl.col("shares_outstanding")).replace(0, None)
            enriched = enriched.with_columns([
                mkt_cap.alias("mkt_cap"),
                (mkt_cap / pl.col("net_income").replace(0, None)).alias("pe_ratio"),
                (pl.col("close") / (pl.col("equity") / pl.col("shares_outstanding")).replace(0, None)).alias("pb_ratio"),
                ((mkt_cap + pl.col("long_term_debt").fill_null(0) + pl.col("short_term_debt").fill_null(0) - pl.col("cash").fill_null(0)) / (pl.col("operating_income") + pl.col("da_expense").fill_null(0)).replace(0, None)).alias("ev_ebitda")
            ])

            # 2. Qualité & Intensité (Quality & Efficiency)
            enriched = enriched.with_columns([
                (pl.col("net_income") / pl.col("equity").replace(0, None)).alias("roe"),
                (pl.col("net_income") / pl.col("total_assets").replace(0, None)).alias("roa"),
                ((pl.col("revenue") - pl.col("cogs").fill_null(0)) / pl.col("revenue").replace(0, None)).alias("gross_margin"),
                # Intensités (% du Revenu) - TRÈS UTILE POUR COMPARER
                (pl.col("rd_expense").fill_null(0) / pl.col("revenue").replace(0, None)).alias("rd_intensity"),
                (pl.col("sga_expense").fill_null(0) / pl.col("revenue").replace(0, None)).alias("sga_intensity"),
                (pl.col("capex").fill_null(0) / pl.col("revenue").replace(0, None)).alias("capex_intensity"),
                # Free Cash Flow Margin
                ((pl.col("operating_cash_flow") - pl.col("capex").fill_null(0)) / pl.col("revenue").replace(0, None)).alias("fcf_margin")
            ])

            # 3. Croissance (Growth YoY)
            enriched = enriched.with_columns([
                (pl.col("revenue") / pl.col("revenue").shift(252).replace(0, None) - 1).alias("rev_growth_yoy"),
                (pl.col("net_income") / pl.col("net_income").shift(252).replace(0, None) - 1).alias("ni_growth_yoy")
            ])

            # Ajout Secteurs
            sector_v = str(meta["sector"]) if meta["sector"] else "Unknown"
            industry_v = str(meta["industry"]) if meta["industry"] else "Unknown"
            enriched = enriched.with_columns([
                pl.lit(sector_v).alias("sector"),
                pl.lit(industry_v).alias("industry")
            ])

            # --- SÉLECTION FINALE (TOUTES LES DONNÉES SONT GARDÉES) ---
            # On garde les ratios ET les données brutes pour que l'utilisateur puisse faire ses propres calculs
            table = enriched.to_arrow()
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression='zstd')
            writer.write_table(table)
            count_success += 1

    if writer:
        writer.close()
    print(f"\n✅ Alpha Master Matrix built with all metrics: {output_path}")

if __name__ == "__main__":
    generate_alpha_matrix_master()
