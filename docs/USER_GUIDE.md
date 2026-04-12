# User Guide: SMID-SEC Quantitative Terminal

## 1. Overview

The `smid.py` Command Line Interface (CLI) serves as the primary gateway for researchers to interact with the SMID-SEC Data Engine. It provides tools for system diagnostics, high-fidelity asset inspection, and the generation of research-ready data subsets for systematic backtesting.

## 2. System Diagnostics and Status

### 2.1 `status` Command
The `status` command performs a structural audit of the underlying Alpha Matrix. It validates the integrity of the Parquet master file and returns key performance indicators of the universe coverage.

**Execution:**
```bash
python3 smid.py status
```

**Expected Diagnostic Output:**
```text
+-----------------------------------------------------------+
| SMID-SEC DATA ENGINE | SYSTEM DIAGNOSTIC                  |
+-----------------------------------------------------------+
| Row Count (Observations) | 12,450,230                     |
| Unique CIK (Universe)    | 8,421                          |
| Start Date               | 2010-01-04                     |
| End Date                 | 2024-06-30                     |
| Storage Format           | Apache Parquet (Zstd)          |
+-----------------------------------------------------------+
```

## 3. Asset Analysis and Universe Screening

### 3.1 `terminal [TICKER]` Command
The `terminal` command provides a comprehensive "Point-in-Time" view of a single asset's fundamentals and valuation metrics. It is used to verify signal incorporation (e.g., impact of a 10-K filing on the Trailing Twelve Months ROE).

**Execution:**
```bash
python3 smid.py terminal NVDA
```

**Output Characteristics:**
The output is partitioned into header metrics (Price, Market Cap, Ratios) and historical quarterly performance tables, with TTM normalization and temporal validation checks applied.

### 3.2 `screen` Command
The `screen` command implements vectorized filtering across the entire US SMID universe. It allows researchers to identify assets that meet specific fundamental and technical criteria at a given timestamp.

**Key Parameters:**
- `--sector`: Filter by SEC-defined industry classification.
- `--roe-min`: Minimum threshold for Return on Equity (Quality Factor).
- `--pe-max`: Maximum threshold for Price-to-Earnings Ratio (Value Factor).
- `--mom-min`: Minimum threshold for 12-month relative price strength (Momentum Factor).

**Institutional Use Case:**
Identifying high-quality, cash-flow generative technology companies with reasonable valuations:
```bash
python3 smid.py screen --sector Technology --roe-min 0.25 --pe-max 20
```

## 4. Research Data Extraction (Backtesting)

### 4.1 `export` Command
To facilitate high-speed backtesting, the `export` command generates surgical, research-ready Parquet files. This prevents the computational overhead of loading the full 40GB+ master matrix into memory.

**Workflow for Systematic Research:**
1.  **Define Universe:** Specify the temporal window and liquidity constraints (ADV).
2.  **Filter Columns:** Select only the alpha factors required for the specific strategy.
3.  **Execute Export:**
    ```bash
    python3 smid.py export --output value_factor_research.parquet \
                           --start 2015-01-01 \
                           --cols pe_ratio,pb_ratio,fcf_yield \
                           --min-adv 5000000
    ```

4.  **Analysis:** Load the resulting `value_factor_research.parquet` file into a research environment (e.g., Jupyter, VectorBT) for strategy simulation.

---
*Precision Engineering for Quantitative Research.*
