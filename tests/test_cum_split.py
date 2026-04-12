import polars as pl

ALPHA_MATRIX_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"
df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == "nvda").collect().sort("p_date", descending=True)

# Tiingo splitFactor: 10.0 signifie split 10-for-1.
# On doit calculer le produit cumulé inversé.
df = df.with_columns([
    (pl.col("close") / pl.col("adjClose")).alias("raw_ratio")
])

# Market Cap économique = adjClose * (shares_SEC * ratio_au_moment_du_rapport)
# Mais comme le ratio change, on doit le verrouiller.

print(df.filter((pl.col("p_date") >= pl.date(2024, 5, 30)) & (pl.col("p_date") <= pl.date(2024, 6, 15)))
      .select(["p_date", "close", "adjClose", "raw_ratio", "shares_outstanding"]))
