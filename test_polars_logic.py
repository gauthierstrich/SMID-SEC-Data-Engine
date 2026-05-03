import polars as pl
from datetime import date

df = pl.DataFrame({
    "cik": ["1"] * 5,
    "e_date": [date(2020, 3, 31), date(2020, 6, 30), date(2020, 9, 30), date(2020, 12, 31), date(2020, 3, 31)],
    "f_date": [date(2020, 5, 1), date(2020, 8, 1), date(2020, 11, 1), date(2021, 3, 1), date(2021, 3, 15)],
    "tag": ["net_income"] * 5,
    "val": [10.0, 15.0, 20.0, 25.0, 12.0] # 12.0 is restatement of Q1
})

df_q_piv = df.pivot(values="val", index=["e_date", "f_date"], on="tag", aggregate_function="last")
f_dates_df = df_q_piv.select(["f_date"]).unique().sort("f_date")
pit_state = f_dates_df.join(df_q_piv, how="cross")
pit_state = pit_state.filter(pl.col("f_date_right") <= pl.col("f_date"))
pit_state = pit_state.sort(["f_date", "e_date", "f_date_right"]).group_by(["f_date", "e_date"]).last()

top4_quarters = pit_state.sort(["f_date", "e_date"], descending=[False, True]).group_by("f_date", maintain_order=True).head(4)
print(top4_quarters)

ttm_cols = ["net_income"]
agg_exprs = [
    pl.col("e_date").min().alias("min_e_date"),
    pl.col("e_date").max().alias("max_e_date"),
    pl.len().alias("q_count")
] + [pl.col(tag).sum().alias(f"{tag}_ttm") for tag in ttm_cols]

ttm_agg = top4_quarters.group_by("f_date").agg(agg_exprs)
ttm_agg = ttm_agg.with_columns((pl.col("max_e_date") - pl.col("min_e_date")).dt.total_days().alias("ttm_days"))

for tag in ttm_cols:
    ttm_agg = ttm_agg.with_columns(
        pl.when((pl.col("q_count") == 4) & (pl.col("ttm_days") >= 330) & (pl.col("ttm_days") <= 390))
        .then(pl.col(f"{tag}_ttm"))
        .otherwise(None)
        .alias(f"{tag}_ttm")
    )

print(ttm_agg.sort("f_date"))

