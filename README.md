# SMID-SEC Data Engine: Institutional-Grade Quantitative Infrastructure

## Overview

The **SMID-SEC Data Engine** is a high-performance financial data pipeline designed for the rigorous requirements of quantitative research and systematic trading within the U.S. Small and Mid-Cap (SMID) universe. The system bridges the structural gap between raw SEC EDGAR filings and market price data, producing a **Point-in-Time (PIT)** and **Survivorship-Bias Free** dataset ready for alpha factor synthesis.

This infrastructure is engineered to eliminate the common pitfalls of backtesting, such as look-ahead bias and data leakage, by enforcing a strict temporal alignment between information availability and its inclusion in the signal matrix.

---

## Technical Pillars

### 1. Economic Invariance Methodology ($N_t$)
To solve the structural conflict between the SEC's administrative latency and the market's immediate price adjustments (splits), the engine implements a **Time-Series Normalized Shares ($N_t$)** model. 

Traditional market cap calculations often suffer from a "valuation cliff" during stock splits because SEC share counts are only updated quarterly. Our methodology calculates an invariant capital factor $N$ at each filing date:
$$N = \frac{Price_{Raw} \times Shares_{SEC}}{Price_{Adjusted}}$$
This factor remains stable through splits and is only updated when a genuine change in the capital structure (buybacks or issuance) is officially reported to the SEC.

### 2. Temporal Validation Logic (TTM 10/10)
Standard Trailing Twelve Months (TTM) calculations often ignore fiscal year shifts or missing reports. The SMID-SEC Data Engine implements a **Temporal Distance Check**:
*   A TTM window is only validated if the span between the four quarters is between 330 and 390 days.
*   This ensures that the Price-to-Earnings (P/E) and other fundamental ratios are calculated over a true annual period, preventing distorted signals during accounting period transitions.

### 3. Point-in-Time (PIT) Integrity
The engine strictly separates the **Fiscal Period End Date** from the **Official Filing Date** (`filed_date`). Signals are only updated on the day the data becomes public via the SEC EDGAR system, ensuring that backtests reflect the information actually available to the market at that specific timestamp.

### 4. Memory-Efficient Streaming Architecture
To handle the high-volume data requirements of the SMID universe without saturating system resources, the engine utilizes a **Lazy Evaluation & Streaming** model powered by Polars. Data is processed per-ticker in isolated memory buffers, allowing for the processing of millions of historical data points on standard research workstations.

---

## Project Structure

```text
.
├── smid.py                 # Core CLI Research Terminal
├── engine/                 # Production Data Pipeline (Bronze -> Silver -> Alpha)
│   ├── pipeline/           # ETL Scripts (00 to 06)
│   ├── registry/           # Ticker & CIK Master Tracking
│   └── config/             # System Settings
├── research/               # Quantitative Strategy Research
│   └── backtests/          # Backtest scripts & performance charts
├── tests/                  # Integrity & Accuracy Validation
│   └── audit/              # Institutional-grade data audits
├── tools/                  # Maintenance & Debugging utilities
│   └── debug/              # Bug reproduction and data fixing
├── docs/                   # Documentation & Intelligence
│   ├── planning/           # Roadmaps & project management
│   ├── reports/            # Audit & certification reports
│   └── ...                 # Technical methodologies
├── requirements.txt        # Dependency Management
└── .env.example            # Environment Configuration
```

---

## Operational Interface

### Research Terminal
The system includes a professional command-line interface for deep-dive company analysis.

**Example Command:**
```bash
python3 smid.py terminal NVDA
```

**Example Output:**
```text
+-----------------------------------------------------------+
| NVDA | Technology | Semiconductors                        |
|                                                           |
| Price: $124.50 | Market Cap: $3050.2B | P/E: 74.2 | ROE: 92.4%|
+-----------------------------------------------------------+
| QUARTERLY PERFORMANCE HISTORY (TTM Normalized)            |
|-----------------------------------------------------------|
| Date       | Revenue (M) | Net Income (M) | P/E Ratio     |
| 2024-06-30 | 26,044      | 14,881         | 74.2          |
| 2024-03-31 | 22,103      | 12,285         | 78.5          |
| 2023-12-31 | 18,120      | 9,243          | 62.1          |
+-----------------------------------------------------------+
```

---

## Deployment and Setup

1. **Environment Initialization:**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Credential Management:**
   Configure `.env` with institutional API access tokens for Tiingo and SEC EDGAR identification.

3. **Pipeline Execution:**
   The orchestrator manages the full data lifecycle:
   ```bash
   python3 engine/pipeline/00_orchestrator.py
   ```

---
*Precision Engineering for Quantitative Research.*
