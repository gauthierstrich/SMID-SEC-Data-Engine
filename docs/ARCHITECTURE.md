# System Architecture: SMID-SEC Data Engine

## 1. Architectural Intent

The **SMID-SEC Data Engine** is designed to address the "Dirty Data" problem in quantitative finance. Specifically, it targets the synchronization issues between administrative filings (SEC) and market transaction data (Tiingo). The architecture follows a strict three-tier data lineage model (Bronze, Silver, Alpha) to ensure traceability and auditability of every signal produced.

## 2. Core Methodologies

### 2.1 Economic Invariance ($N_t$) for Market Capitalization

The primary challenge in historical market capitalization calculation is the decoupling of price and share count during corporate actions (splits). 

**Traditional Method (Flawed):**
$$\text{Market Cap}_{t} = Price_{Adjusted, t} \times Shares_{SEC, \text{latest known}}$$
*Failure:* During a 10-to-1 split, the $Price_{Adjusted}$ remains stable, but if the SEC shares are not updated for 2 months, the Market Cap appears 10x smaller than reality, creating a massive look-ahead bias and false buy signals.

**SMID-SEC $N_t$ Method:**
We define a "Normalized Share Count" ($N$) as the anchor:
$$N_{filing} = \frac{Price_{Raw, filing} \times Shares_{SEC, filing}}{Price_{Adjusted, filing}}$$
Where $N_{filing}$ represents the total equity value expressed in adjusted price units. This factor is calculated strictly on the `filed_date` and forward-filled until the next official report.
$$\text{Market Cap}_{t} = Price_{Adjusted, t} \times N_{t}$$
This ensures continuity and eliminates the split-induced valuation cliffs.

### 2.2 Temporal Validation (TTM 10/10)

To ensure the integrity of Trailing Twelve Months (TTM) metrics, the engine implements a temporal distance validator. For any given reporting date $T$, the TTM sum is only generated if:
$$330 \leq Days(End\_Date_{T} - End\_Date_{T-3}) \leq 390$$
This heuristic handles:
- Leap years.
- Slight shifts in fiscal quarter ends.
- **Fail-safe:** If an enterprise fails to report or shifts its fiscal year significantly, the metric is invalidated rather than returning a corrupted sum.

### 2.3 Unit and Currency Normalization

SEC filings often contain mixed units (Thousands vs. Millions) or secondary currencies. The refinery layer (`05_silver_fundamentals_refinery.py`) implements a strict whitelist:
- **Currency:** `USD` only. Any non-USD facts are rejected to prevent currency contamination of ratios (P/E, P/B).
- **Shares:** `shares` unit only.
- **Scaling:** Data is read as raw integers from XBRL facts to prevent rounding errors or scaling mismatches common in third-party data providers.

## 3. Data Flow and Infrastructure

### 3.1 Lineage Diagram

```text
[ RAW SOURCE ]          [ BRONZE LAYER ]          [ SILVER LAYER ]          [ ALPHA LAYER ]
       |                       |                         |                         |
SEC XBRL JSON --------> sec_facts/*.json --------> fundamentals.parquet ----------+
                               |                         |                        |
                               | (Normalization)         | (Unit Check)           |
                               v                         v                        |
Tiingo API OHLCV -----> prices/*.csv -----------> prices_master.parquet ----------+
                               |                         |                        |
                               | (Vectorization)         | (Split Correction)     |
                               v                         v                        |
                               |                         |                        |
                               +-------------------------+------------------------+
                                                         |
                                                         v
                                              [ 06_alpha_engine.py ]
                                              (Streaming Processing)
                                                         |
                                                         v
                                              [ ALPHA_MATRIX_MASTER ]
                                              (Point-in-Time Matrix)
```

### 3.2 Memory Management Strategy (Streaming)

Given the potential size of the US SMID universe, a naive "Load All" strategy results in OOM (Out of Memory) errors. The engine utilizes a **Filtered Streaming Loop**:
1.  **Lazy Scanning:** `pl.scan_parquet` initializes pointers to the master files without loading data.
2.  **Ticker Isolation:** The main loop processes one `permaTicker` at a time.
3.  **Sink Partitioning:** The final matrix is written using a `ParquetWriter` which flushes buffers to disk, maintaining a constant memory footprint regardless of the dataset size.

## 4. Pipeline Robustness and Fault Tolerance

### 4.1 Distributed Ingestion Logic
The ingestion engine is engineered for unreliable network environments:
- **Exponential Backoff:** Implements a jitter-based retry mechanism for API rate limits (HTTP 429).
- **Atomic Writes:** Data is written to temporary buffers before being committed to the Bronze layer, preventing file corruption.
- **State Persistence:** The `master_tracker.csv` acts as a distributed state machine, allowing the pipeline to resume from the point of failure.

### 4.2 Data Lineage and Traceability
Every data point in the final Alpha Matrix can be traced back to its raw source:
1. **Source Identifiers:** We preserve the SEC Accession Number (`accn`) and Tiingo `permaTicker` throughout the transformation.
2. **Audit Trails:** The `integrity_check.py` suite allows for systematic verification of outputs against historical benchmarks.

## 5. Technical Stack

- **Engine:** Python 3.12 (Strongly typed).
- **Processing:** Polars (Rust-backed DataFrames) for multi-threaded vectorization.
- **Storage:** Apache Parquet with Zstandard (Zstd) compression.
- **Joining Strategy:** `join_asof` (Backwards) to ensure Point-in-Time alignment.

---
*Developed for Institutional-Grade Quantitative Research.*
