import polars as pl
import os
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION DYNAMIQUE DES CHEMINS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

# Priorité 1: Variable d'environnement (si définie dans .env)
# Priorité 2: Détection automatique d'un dossier 'storage' à la racine du projet
DEFAULT_STORAGE = os.path.join(BASE_DIR, "storage")
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", DEFAULT_STORAGE)

SILVER_DIR = os.path.join(LACIE_STORAGE, "silver")
PRICE_PATH = os.path.join(SILVER_DIR, "prices_master.parquet")
FUND_PATH = os.path.join(SILVER_DIR, "fundamentals_master.parquet")
META_PATH = os.path.join(SILVER_DIR, "metadata_master.parquet")

def normalize_cik(val):
    if val is None: return "0000000000"
    try: return str(int(float(val))).zfill(10)
    except: return str(val).zfill(10)

def is_common_stock(ticker):
    if not ticker: return False
    t = ticker.upper()
    if any(suffix in t for suffix in ["-P", "_P", "PR", "WS", "-W", ".U", " WRT"]): return False
    if len(t) > 5: return False
    return True

def generate_alpha_matrix_master():
    print("🚀 [PHASE 6.8] Final Reconstruction - RAM OPTIMIZED (Stream Mode) - PIT FIXED")
    output_path = os.path.join(SILVER_DIR, "alpha_matrix_master.parquet")
    if os.path.exists(output_path): os.remove(output_path)

    # 1. Load Meta
    df_meta = pl.read_parquet(META_PATH).with_columns(
        pl.col("cik").map_elements(normalize_cik, return_dtype=pl.String).alias("cik_clean")
    )
    df_meta = df_meta.filter(pl.col("ticker").map_elements(is_common_stock, return_dtype=pl.Boolean))
    meta_dict = {row['permaTicker']: row for row in df_meta.to_dicts()}

    # 2. Scanner les fondamentaux
    df_f_scan = pl.scan_parquet(FUND_PATH).with_columns(pl.col("cik").cast(pl.String).str.zfill(10))

    # 3. Schema Arrow pour l'écriture
    arrow_schema = pa.schema([
        ('ticker', pa.large_string()), ('cik', pa.large_string()), ('p_date', pa.date32()),
        ('close', pa.float64()), ('adjClose', pa.float64()), ('volume', pa.float64()),
        ('sector', pa.large_string()), ('industry', pa.large_string()), ('mkt_cap', pa.float64()),
        ('pe_ratio', pa.float64()), ('pb_ratio', pa.float64()), ('roe', pa.float64()),
        ('roa', pa.float64()), ('gross_margin', pa.float64()), ('rev_growth_yoy', pa.float64()),
        ('mom_12m', pa.float64()), ('adv_20d', pa.float64()),
        ('debt_to_equity', pa.float64()), ('fcf_yield', pa.float64()), ('ev', pa.float64()), ('ev_to_ebit', pa.float64()),
        ('revenue', pa.float64()), ('net_income', pa.float64()), ('cogs', pa.float64()),
        ('operating_income', pa.float64()), ('rd_expense', pa.float64()), ('sga_expense', pa.float64()),
        ('operating_cash_flow', pa.float64()), ('capex', pa.float64()),
        ('revenue_fy', pa.float64()), ('net_income_fy', pa.float64()), ('cogs_fy', pa.float64()),
        ('operating_income_fy', pa.float64()), ('rd_expense_fy', pa.float64()), ('sga_expense_fy', pa.float64()),
        ('shares_outstanding', pa.float64()), ('equity', pa.float64()), ('total_assets', pa.float64()),
        ('cash', pa.float64()), ('long_term_debt', pa.float64()), ('short_term_debt', pa.float64())
    ])
    
    unique_tickers = df_meta["permaTicker"].unique().to_list()
    writer = pq.ParquetWriter(output_path, arrow_schema, compression='zstd')
    df_p_scan = pl.scan_parquet(PRICE_PATH)

    base_tags = ["net_income", "revenue", "operating_income", "operating_cash_flow", "capex", "equity", "total_assets", "cash", "long_term_debt", "short_term_debt", "cogs", "rd_expense", "sga_expense"]
    ttm_base_cols = ["net_income", "revenue", "operating_income", "operating_cash_flow", "capex"]

    for pt in tqdm(unique_tickers, desc="Stream Matrix Processing"):
        meta = meta_dict.get(pt)
        if not meta: continue
        cik = meta["cik_clean"]
        
        # --- CHARGEMENT CIBLÉ ---
        ticker_funds_raw = df_f_scan.filter(pl.col("cik") == cik).collect()
        if ticker_funds_raw.is_empty(): continue
        
        ticker_funds_raw = ticker_funds_raw.with_columns([
            pl.col("end_date").str.to_date("%Y-%m-%d").alias("e_date"),
            pl.col("filed_date").str.to_date("%Y-%m-%d").alias("f_date")
        ]).filter(pl.col("f_date").is_not_null())

        # --- 1. BUILD PIT TTM ---
        df_q = ticker_funds_raw.filter(pl.col("is_quarter") == True)
        if not df_q.is_empty():
            df_q_piv = df_q.pivot(values="val", index=["e_date", "f_date"], on="tag", aggregate_function="last")
            
            f_dates_df = df_q_piv.select(["f_date"]).unique().sort("f_date")
            
            pit_state = f_dates_df.join(df_q_piv, how="cross")
            pit_state = pit_state.filter(pl.col("f_date_right") <= pl.col("f_date"))
            
            pit_state = pit_state.sort(["f_date", "e_date", "f_date_right"]).group_by(["f_date", "e_date"]).last()
            top4_quarters = pit_state.sort(["f_date", "e_date"], descending=[False, True]).group_by("f_date", maintain_order=True).head(4)
            
            ttm_cols = [t for t in ttm_base_cols if t in top4_quarters.columns]
            
            agg_exprs = [
                pl.col("e_date").min().alias("min_e_date"),
                pl.col("e_date").max().alias("max_e_date"),
                pl.len().alias("q_count")
            ] + [pl.col(tag).sum().alias(f"{tag}_ttm") for tag in ttm_cols]
            
            ttm_agg = top4_quarters.group_by("f_date").agg(agg_exprs)
            ttm_agg = ttm_agg.with_columns((pl.col("max_e_date") - pl.col("min_e_date")).dt.total_days().alias("ttm_days"))
            
            # FIX: TTM distance between end of Q1 and end of Q4 is ~275 days (9 months distance).
            for tag in ttm_cols:
                ttm_agg = ttm_agg.with_columns(
                    pl.when((pl.col("q_count") == 4) & (pl.col("ttm_days") >= 265) & (pl.col("ttm_days") <= 285))
                    .then(pl.col(f"{tag}_ttm"))
                    .otherwise(None)
                    .alias(f"{tag}_ttm")
                )
            ttm_agg = ttm_agg.drop(["min_e_date", "max_e_date", "q_count", "ttm_days"])
        else:
            ttm_agg = pl.DataFrame({"f_date": [], **{f"{tag}_ttm": [] for tag in ttm_base_cols}}, schema={"f_date": pl.Date, **{f"{tag}_ttm": pl.Float64 for tag in ttm_base_cols}})

        # --- 2. BUILD INSTANT AND FY TAGS ---
        df_arr = ticker_funds_raw.pivot(values="val", index=["e_date", "f_date"], on="tag", aggregate_function="last")
        
        df_fy = ticker_funds_raw.filter(pl.col("is_fy") == True).pivot(values="raw_val", index=["e_date", "f_date"], on="tag", aggregate_function="last")
        rename_map = {col: f"{col}_fy" for col in df_fy.columns if col not in ["e_date", "f_date"]}
        df_fy = df_fy.rename(rename_map)
        
        df_comb = df_arr.join(df_fy, on=["e_date", "f_date"], how="left")
        df_comb = df_comb.sort(["f_date", "e_date"]).group_by("f_date").last()
        
        # --- 3. MERGE TTM AND COMBINED ---
        ticker_funds_combined = df_comb.join(ttm_agg, on="f_date", how="left").sort("f_date")
        
        for tag in base_tags:
            if tag not in ticker_funds_combined.columns:
                ticker_funds_combined = ticker_funds_combined.with_columns(pl.lit(None).cast(pl.Float64).alias(tag))
        for tag in ttm_base_cols:
            ttm_tag = f"{tag}_ttm"
            fy_tag = f"{tag}_fy"
            if ttm_tag not in ticker_funds_combined.columns:
                ticker_funds_combined = ticker_funds_combined.with_columns(pl.lit(None).cast(pl.Float64).alias(ttm_tag))
            if fy_tag in ticker_funds_combined.columns:
                ticker_funds_combined = ticker_funds_combined.with_columns(
                    pl.when(pl.col(fy_tag).is_not_null())
                    .then(pl.col(fy_tag))
                    .otherwise(pl.col(ttm_tag))
                    .alias(ttm_tag)
                )

        for tag in ["revenue_fy", "net_income_fy", "cogs_fy", "operating_income_fy", "rd_expense_fy", "sga_expense_fy"]:
            if tag not in ticker_funds_combined.columns:
                ticker_funds_combined = ticker_funds_combined.with_columns(pl.lit(None).cast(pl.Float64).alias(tag))

        # --- 4. JOIN PRIX ---
        prices = df_p_scan.filter(pl.col("permaTicker") == pt).collect()
        if prices.is_empty(): continue
        
        enriched = prices.with_columns([
            pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date"),
            (pl.col("adjClose") * pl.col("adjVolume")).alias("dollar_volume")
        ]).sort("p_date")
        
        enriched = enriched.with_columns([
            (pl.col("adjClose") / pl.col("adjClose").shift(252).replace(0, None) - 1).alias("mom_12m"),
            pl.col("dollar_volume").rolling_mean(window_size=20).alias("adv_20d")
        ])
        
        enriched = enriched.join_asof(ticker_funds_combined, left_on="p_date", right_on="f_date")
        
        cols_to_ffill = [c for c in ticker_funds_combined.columns if c not in ["f_date", "e_date"]]
        enriched = enriched.with_columns([
            pl.col(c).forward_fill() for c in cols_to_ffill if c in enriched.columns
        ])

        # --- 5. CALCUL MARKET CAP (N_t Method) ---
        shares_timeline = ticker_funds_raw.filter(pl.col("tag") == "shares_outstanding").select(["f_date", "val"]).rename({"val": "shares_sec"})
        shares_timeline = shares_timeline.sort(["f_date", "shares_sec"]).group_by("f_date").last()
        
        enriched = enriched.join(shares_timeline, left_on="p_date", right_on="f_date", how="left")
        enriched = enriched.with_columns(
            ((pl.col("close") * pl.col("shares_sec")) / pl.col("adjClose").replace(0, None)).alias("n_at_filing")
        ).with_columns(
            pl.col("n_at_filing").forward_fill().alias("n_shares")
        )
        
        mkt_cap = (pl.col("adjClose") * pl.col("n_shares")).replace(0, None)
        total_debt = pl.col("long_term_debt").fill_null(0) + pl.col("short_term_debt").fill_null(0)
        ev = mkt_cap + total_debt - pl.col("cash").fill_null(0)
        fcf = pl.col("operating_cash_flow_ttm").fill_null(0) - pl.col("capex_ttm").fill_null(0).abs()
        
        enriched = enriched.with_columns([
            mkt_cap.alias("mkt_cap"),
            (mkt_cap / pl.col("net_income_ttm").replace(0, None)).alias("pe_ratio"),
            (mkt_cap / pl.col("equity").replace(0, None)).alias("pb_ratio"),
            (pl.col("net_income_ttm") / pl.col("total_assets").replace(0, None)).alias("roe"),
            (pl.col("net_income_ttm") / pl.col("total_assets").replace(0, None)).alias("roa"),
            ((pl.col("revenue").fill_null(0) - pl.col("cogs").fill_null(0)) / pl.col("revenue").replace(0, None)).alias("gross_margin"),
            (pl.col("revenue_ttm") / pl.col("revenue_ttm").shift(252).replace(0, None) - 1).alias("rev_growth_yoy"),
            (total_debt / pl.col("equity").replace(0, None)).alias("debt_to_equity"),
            (fcf / mkt_cap.replace(0, None)).alias("fcf_yield"),
            ev.alias("ev"),
            (ev / pl.col("operating_income_ttm").replace(0, None)).alias("ev_to_ebit"),
            pl.lit(str(meta.get("sector", "Unknown"))).alias("sector"),
            pl.lit(str(meta.get("industry", "Unknown"))).alias("industry"),
            pl.lit(cik).alias("cik")
        ])

        for col_name in arrow_schema.names:
            if col_name not in enriched.columns:
                enriched = enriched.with_columns(pl.lit(None).cast(pl.Float64).alias(col_name))

        final_chunk = enriched.select(arrow_schema.names).with_columns([
            pl.col(c).cast(pl.String) for c in ["ticker", "cik", "sector", "industry"]
        ])
        writer.write_table(final_chunk.to_arrow())

    writer.close()
    print(f"✅ QUANT MASTER MATRIX BUILT (STREAMING MODE): {output_path}")

if __name__ == "__main__":
    generate_alpha_matrix_master()
