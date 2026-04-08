# 🏛️ SMID-SEC Data Engine

**SMID-SEC Data Engine** is a high-performance financial data pipeline designed to build a "Survivorship-Bias Free" dataset for the US Small & Mid Caps (SMID) universe. It bridges the gap between raw SEC EDGAR filings and quantitative research.

---

## 🚀 Key Features

*   **Survivorship-Bias Free:** Tracks all tickers, including delisted ("Ghost") stocks.
*   **SEC EDGAR Integration:** Direct extraction of fundamental facts (XBRL) from the SEC.
*   **Tiingo Integration:** High-quality historical price data.
*   **Silver Layer Refinery:** Automated cleaning, CIK matching, and signal generation.
*   **Alpha Engine:** Generates a daily `alpha_matrix` in Parquet format for instant backtesting.

---

## 🛠️ Architecture: The Pipeline

The engine operates in sequential phases located in `engine/pipeline/`:

1.  **`01_bootstrap_registry.py`**: Initializes the `master_tracker.csv` from SEC and Tiingo listings.
2.  **`02_sec_mirror.py`**: Maps CIKs to tickers and metadata.
3.  **`03_price_vacuum.py`**: Downloads historical prices from Tiingo.
4.  **`04_sec_fundamentals.py`**: Downloads raw fundamental facts (JSON) from SEC EDGAR.
5.  **`05_silver_refinery.py`**: Cleans and normalizes price data.
6.  **`05_silver_fundamentals_refinery.py`**: Extracts and normalizes fundamentals.
7.  **`06_alpha_engine.py`**: Fuses everything into a master Alpha Matrix.

**Orchestration**: `00_orchestrator.py` monitors and retries failed downloads automatically.

---

## 💻 Setup & Installation

### 1. Requirements
*   Python 3.10+
*   At least 16GB RAM (for Silver Layer refinery)
*   ~50GB of disk space (depending on history depth)

### 2. Installation
```bash
git clone https://github.com/GauthierStrich/SMID-SEC-Data-Engine.git
cd SMID-SEC-Data-Engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
*   `TIINGO_API_KEY`: Your Tiingo API key.
*   `LACIE_STORAGE_PATH`: Path to where the bulk data (Bronze/Silver) will be stored.
*   `PROJECT_ROOT`: Absolute path to this repository.

---

## 🎯 Usage

The main interface is `smid.py`:

*   **Check Status**: `python3 smid.py status`
*   **Get Ticker Data**: `python3 smid.py get [TICKER]`
*   **Screen Market**: `python3 smid.py screen --roe-min 0.15 --pe-max 20`
*   **Export for Backtest**: `python3 smid.py export --output my_data.parquet`

---

## 📜 Documentation
Detailed specs are available in the `docs/` folder:
*   [CONTEXT.md](docs/CONTEXT.md): Project philosophy and history.
*   [USER_GUIDE.md](docs/USER_GUIDE.md): Detailed CLI usage.
*   [ALPHA_MATRIX_SPEC.md](docs/ALPHA_MATRIX_SPEC.md): Signal definitions and math.

---
*Developed for Institutional-Grade Quantitative Research.*
