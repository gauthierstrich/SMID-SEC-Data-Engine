# 📖 USER GUIDE: SMID-SEC QUANT TERMINAL

The `smid.py` CLI is the command-line interface for interacting with the data infrastructure. This guide details the research and deployment capabilities of the terminal.

---

## 🚦 Operational Status

### `status`: System Diagnostic
The `status` command provides a high-level audit of the Alpha Matrix. It scans the Parquet master file and returns:
*   Total row count (Observation points).
*   Unique ticker count (Universe size).
*   Temporal coverage (Start/End dates).
```bash
python3 smid.py status
```

---

## 🔍 Market Intelligence & Screening

### `get [TICKER]`: Single Asset Inspection
Returns the most recent 10 days of enriched data for a specific ticker. This is the primary tool for verifying signal integrity (e.g., checking if a recent earnings report was correctly incorporated into the ROE calculation).
```bash
python3 smid.py get AAPL
```

### `screen`: Multi-Factor Universe Filtering
The `screen` command enables real-time filtering across the entire US SMID universe based on fundamental and technical signals.

**Primary Arguments:**
*   `--date`: Target observation date (Default: Latest).
*   `--sector`: Restrict to a specific SEC Sector (e.g., `Technology`, `Healthcare`).
*   `--pe-max`: Valuation filter (Price-to-Earnings).
*   `--roe-min`: Quality filter (Return on Equity).
*   `--mom-min`: Momentum filter (12-month relative strength).

**Example: Finding high-quality, undervalued tech stocks:**
```bash
python3 smid.py screen --sector Technology --roe-min 0.20 --pe-max 18
```

---

## 📥 Research Workflow (Backtesting)

### `export`: Generating Optimized Backtest Subsets
To avoid loading the entire 40GB+ dataset into memory during backtesting, use the `export` command to create a surgical, research-ready Parquet file.

**Why use Export?**
*   **Speed:** Reduces data loading time from minutes to milliseconds.
*   **Efficiency:** Filters only the tickers and signals needed for your specific strategy.
*   **Safety:** Ensures that the data used in research is an exact point-in-time slice.

**Arguments:**
*   `--output`: Filename for the research subset (e.g., `value_strat_v1.parquet`).
*   `--start` / `--end`: Temporal window for the simulation.
*   `--cols`: Specific alpha signals required (e.g., `pe_ratio,roe,mom_12m`).
*   `--min-adv`: Liquidity filter. Excludes stocks with low Average Daily Volume.

**Workflow Example:**
1.  **Extract:**
    ```bash
    python3 smid.py export --output quality_strat.parquet --start 2015-01-01 --cols roe,debt_to_equity --min-adv 1000000
    ```
2.  **Analyze:** Charge `quality_strat.parquet` into your research notebook for simulation.

---
*Developed for Precision Quantitative Research.*
