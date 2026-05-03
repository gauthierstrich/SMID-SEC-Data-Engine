# SMID-SEC Data Engine: Project Instructions & Conventions

## 🏗️ Architecture & Philosophy
- **CIK-Centric Design:** Always prioritize SEC CIK (Central Index Key) over Ticker symbols for company identification to handle delistings and re-listings accurately.
- **Point-in-Time (PIT) Integrity:** Ensure all signals are aligned with the official `filed_date` to prevent look-ahead bias.
- **Economic Invariance ($N_t$):** Use the $N_t$ methodology for Market Capitalization to remain split-invariant and eliminate "valuation cliffs".
- **Survivorship-Bias Free:** The system must include and track "Ghost" (delisted) companies.

## 🛠️ Technology Stack
- **Engine:** Python 3.12+ (Strongly typed).
- **Data Processing:** Polars (Lazy API) for performance and memory efficiency.
- **Storage:** Apache Parquet with Zstandard (Zstd) compression.
- **CLI:** Rich for terminal output.

## 📁 Storage Conventions
- **Bronze Layer:** Raw JSON/CSV files from SEC and Tiingo.
- **Silver Layer:** Refined Parquet files (fundamentals_master, prices_master, alpha_matrix_master).
- **Default Path:** `storage/` directory at the project root, or path specified in `LACIE_STORAGE_PATH` env var.

## 🧪 Development Workflow
- **Validation:** Always use `tests/certification/integrity_check.py` to verify data integrity after significant pipeline changes.
- **Documentation:** Maintain methodology documents in `docs/` and planning in `docs/planning/`.
- **Coding Style:** Clean, typed Python code. Use Polars' lazy evaluation whenever possible to avoid OOM issues.

## 🚨 Critical Rules
- **NEVER** trust a `status = success` without verifying the resulting Parquet files.
- **NO** look-ahead bias: Always use `filed_date` for fundamental data availability.
- **NO** currency contamination: Support only `USD` for financial facts.
