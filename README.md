# 🏛️ SMID-SEC DATA ENGINE

[![Status](https://img.shields.io/badge/Status-Institutional_Grade-blue.svg)]()
[![Backend](https://img.shields.io/badge/Engine-Polars/PyArrow-orange.svg)]()
[![Data](https://img.shields.io/badge/Source-SEC_EDGAR/Tiingo-green.svg)]()

**SMID-SEC Data Engine** is an institutional-grade financial data infrastructure built to produce a **Survivorship-Bias Free** and **Point-in-Time (PIT)** dataset for the US Small & Mid-Cap universe. 

Designed for quantitative researchers, it bridges the gap between raw SEC filings and alpha-ready signal matrices, ensuring maximum historical fidelity for backtesting.

---

## 💎 Core Value Proposition

### 🛡️ Institutional Data Discipline
*   **Zero Survivorship Bias:** Systematic tracking of delisted, bankrupted, and renamed companies ("Ghosts").
*   **Zero Look-ahead Bias:** Fundamental data is strictly aligned with the **Actual SEC Filing Date** (`filed_date`), not the fiscal period end.
*   **CIK-Centric Integrity:** Uses immuable Central Index Keys (CIK) for all data joins, preventing data loss during ticker changes.

### ⚡ High-Performance Architecture
*   **Vectorized Refinery:** Powered by **Polars** (Rust-based) for lightning-fast multi-threaded data processing.
*   **Columnar Storage:** Utilizes **Apache Parquet (zstd)** to reduce storage footprint by 10x while enabling O(1) random access.
*   **Big Data Ready:** Implements incremental chunk-based processing to handle millions of rows within restricted memory environments.

---

## 🏗️ Architecture & Pipeline

The engine operates in three distinct logical layers:

1.  **Bronze Layer (Raw):** Direct ingestion of Tiingo CSVs and SEC EDGAR XBRL JSON Facts.
2.  **Silver Layer (Refinery):** Normalization of disparate GAAP tags and mapping of CIK-to-Ticker relationships.
3.  **Alpha Layer (Signals):** Synthesis of quantitative factors (Value, Quality, Momentum, Volatility).

> 📘 **Deep Dive:** For detailed technical specs, see [SYSTEM ARCHITECTURE](docs/ARCHITECTURE.md).

---

## 🛠️ Quick Start

### 1. Installation
```bash
git clone https://github.com/gauthierstrich/SMID-SEC-Data-Engine.git
cd SMID-SEC-Data-Engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and configure your API keys and storage paths.
```bash
cp .env.example .env
```

### 3. Usage (The Quant Terminal)
The `smid.py` CLI provides direct access to the engine:
*   **Health Check:** `python3 smid.py status`
*   **Screening:** `python3 smid.py screen --roe-min 0.15 --pe-max 15`
*   **Export for Backtest:** `python3 smid.py export --output my_strategy.parquet`

---

## 📜 Documentation Index

| Document | Description |
| :--- | :--- |
| [**Architecture**](docs/ARCHITECTURE.md) | High-level system design and data flow. |
| [**Alpha Spec**](docs/ALPHA_MATRIX_SPEC.md) | Mathematical definitions of signals (P/E, ROE, etc.). |
| [**User Guide**](docs/USER_GUIDE.md) | Detailed CLI usage and examples. |
| [**Context**](docs/CONTEXT.md) | Project genesis and development philosophy. |

---
*Developed for Precision Quantitative Research.*
