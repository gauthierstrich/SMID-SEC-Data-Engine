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
    print("🚀 [PHASE 6.2] Generating Master Alpha Matrix (TTM Edition)...")

    # 1. Load Metadata
    df_meta = pl.read_parquet(META_PATH).select(["permaTicker", "ticker", "cik", "sector", "industry"])
    df_meta = df_meta.with_columns(
        pl.col("cik").map_elements(normalize_cik, return_dtype=pl.String).alias("cik_clean")
    )
    meta_data = {row['permaTicker']: row for row in df_meta.to_dicts()}

    # 2. Pre-process Fundamentals with TTM Logic
    print("📦 Pre-processing Fundamentals (Calculating TTM)...")
    df_f = pl.read_parquet(FUND_PATH)
    df_f = df_f.with_columns(pl.col("cik").cast(pl.String))
    
    # Séparation des flux (besoin de TTM) et des stocks (bilan, pas besoin de TTM)
    flow_tags = ["revenue", "net_income", "operating_income", "operating_cash_flow", "capex", "rd_expense", "sga_expense"]
    
    # Pivot pour avoir une ligne par rapport
    df_f_pivoted = df_f.pivot(
        values="value",
        index=["cik", "end_date", "filed_date", "fp"],
        on="tag",
        aggregate_function="last"
    ).sort(["cik", "end_date"])

    # --- LOGIQUE TTM (Trailing Twelve Months) ---
    # Pour chaque entreprise, on calcule la somme glissante des rapports disponibles
    ttm_expressions = []
    for tag in flow_tags:
        if tag in df_f_pivoted.columns:
            # min_periods=1 permet d'avoir un résultat même si on a moins de 4 rapports (ex: entreprises récentes)
            ttm_expressions.append(
                pl.col(tag).rolling_sum(window_size=4, min_periods=1).over("cik").alias(f"{tag}_ttm")
            )
    
    df_f_ttm = df_f_pivoted.with_columns(ttm_expressions)
    
    # On prépare la date de jointure (filed_date)
    df_f_ttm = df_f_ttm.with_columns(
        pl.col("filed_date").str.to_date("%Y-%m-%d").alias("f_date")
    ).sort("f_date")

    # 3. Setup Output
    output_path = os.path.join(SILVER_DIR, "alpha_matrix_master.parquet")
    if os.path.exists(output_path):
        os.remove(output_path)

    # 4. Sequential Processing
    print("📦 Building Alpha Matrix with TTM Signals...")
    df_p_scan = pl.scan_parquet(PRICE_PATH)
    unique_tickers = df_meta["permaTicker"].unique().to_list()
    
    writer = None
    count_success = 0

    for pt in tqdm(unique_tickers, desc="Processing Tickers"):
        meta = meta_data.get(pt)
        if not meta: continue
        
        ticker_prices = df_p_scan.filter(pl.col("permaTicker") == pt).collect()
        if ticker_prices.is_empty(): continue
        
        enriched = ticker_prices.with_columns([
            pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date"),
            (pl.col("close") * pl.col("volume")).alias("dollar_volume")
        ]).sort("p_date")
        
        # Momentum & Vol
        enriched = enriched.with_columns([
            (pl.col("close") / pl.col("close").shift(1) - 1).alias("daily_return"),
            (pl.col("close") / pl.col("close").shift(252).replace(0, None) - 1).alias("mom_12m")
        ])
        enriched = enriched.with_columns([
            pl.col("daily_return").rolling_std(window_size=30).alias("vol_30d"),
            pl.col("dollar_volume").rolling_mean(window_size=20).alias("adv_20d")
        ])
        
        cik = meta["cik_clean"]
        if not cik or cik == "None": continue
        ticker_funds = df_f_ttm.filter(pl.col("cik") == cik)
        
        if not ticker_funds.is_empty():
            enriched = enriched.join_asof(ticker_funds, left_on="p_date", right_on="f_date")
            if not enriched["f_date"].is_not_null().any(): continue

            # --- CALCUL DES RATIOS BASÉS SUR LE TTM ---
            mkt_cap = (pl.col("close") * pl.col("shares_outstanding")).replace(0, None)
            
            # On vérifie la présence des colonnes TTM
            for tag in flow_tags:
                col_ttm = f"{tag}_ttm"
                if col_ttm not in enriched.columns:
                    enriched = enriched.with_columns(pl.lit(None).cast(pl.Float64).alias(col_ttm))

            enriched = enriched.with_columns([
                mkt_cap.alias("mkt_cap"),
                # VRAI PER TTM : Cap / Bénéfice des 12 derniers mois
                (mkt_cap / pl.col("net_income_ttm").replace(0, None)).alias("pe_ratio"),
                # VRAI ROE TTM : Bénéfice 12m / Capitaux Propres actuels
                (pl.col("net_income_ttm") / pl.col("equity").replace(0, None)).alias("roe"),
                # Croissance TTM : Comparaison du bloc de 12 mois actuel vs bloc de 12 mois précédent
                (pl.col("revenue_ttm") / pl.col("revenue_ttm").shift(252).replace(0, None) - 1).alias("rev_growth_yoy"),
                # Intensité R&D TTM
                (pl.col("rd_expense_ttm").fill_null(0) / pl.col("revenue_ttm").replace(0, None)).alias("rd_intensity")
            ])

            # Ajout Secteurs
            sector_v = str(meta["sector"]) if meta["sector"] else "Unknown"
            enriched = enriched.with_columns([pl.lit(sector_v).alias("sector")])

            # Sélection Finale
            final_cols = ["ticker", "p_date", "close", "sector", "mkt_cap", "pe_ratio", "roe", "rev_growth_yoy", "rd_intensity", "mom_12m", "vol_30d", "adv_20d"]
            final_df = enriched.select([c for col in final_cols if (c := col) in enriched.columns])
            
            table = final_df.to_arrow()
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression='zstd')
            writer.write_table(table)
            count_success += 1

    if writer:
        writer.close()
    print(f"\n✅ Alpha Matrix Master avec TTM générée : {output_path}")

if __name__ == "__main__":
    generate_alpha_matrix_master()
