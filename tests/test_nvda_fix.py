import polars as pl
import os

ALPHA_MATRIX_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"

# On charge les prix et les shares bruts
df = pl.scan_parquet(ALPHA_MATRIX_PATH).filter(pl.col("ticker") == "nvda").collect()

# 1. Identifier les lignes où on a un rapport SEC (shares_outstanding non nul)
# 2. Calculer le 'Synthetic Shares' (Nombre d'actions à l'échelle de l'adjClose)
# Synthetic = (Close_Brut * Shares_SEC) / AdjClose
df = df.with_columns([
    ((pl.col("close") * pl.col("shares_outstanding")) / pl.col("adjClose")).alias("synth_shares")
])

# 3. Porter cette valeur dans le futur (forward fill)
df = df.with_columns([
    pl.col("synth_shares").forward_fill().alias("synth_shares")
])

# 4. Calculer la Market Cap 'Honnête'
df = df.with_columns([
    (pl.col("adjClose") * pl.col("synth_shares")).alias("mkt_cap_honest")
])

# 5. Calculer le PER 'Honnête'
df = df.with_columns([
    (pl.col("mkt_cap_honest") / pl.col("net_income")).alias("pe_honest")
])

# Affichage autour du split
print(df.filter((pl.col("p_date") >= pl.date(2024, 5, 30)) & (pl.col("p_date") <= pl.date(2024, 6, 15)))
      .select(["p_date", "close", "adjClose", "mkt_cap_honest", "pe_honest"]))
