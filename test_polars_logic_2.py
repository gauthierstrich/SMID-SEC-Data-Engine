import polars as pl
from datetime import date

df = pl.DataFrame({
    "e_date": [date(2019, 12, 31), date(2020, 3, 31), date(2020, 6, 30), date(2020, 9, 30), date(2020, 12, 31)],
    "val": [10, 20, 30, 40, 50]
})

df = df.with_columns([
    (pl.col("e_date") - pl.col("e_date").shift(3)).dt.total_days().alias("shift_3_days"),
    (pl.col("e_date") - pl.col("e_date").shift(4)).dt.total_days().alias("shift_4_days")
])

print(df)
