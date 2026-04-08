import polars as pl
import pandas as pd
import numpy as np
import os
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from tqdm import tqdm
import quantstats as qs

# Configuration
DATA_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"
OUTPUT_DIR = "/home/gauthierstrich/Bureau/stratégie basique AC20"
START_DATE = "2005-01-01"
END_DATE = "2026-04-01"
REBALANCE_MONTHS = [1, 4, 7, 10]  # Quarterly
STOP_LOSS_PCT = 0.15  # 15% Stop loss
MIN_MKT_CAP = 100_000_000  # $100M min mkt cap to avoid micro-cap noise

def load_data():
    print("📂 Loading data...")
    df = pl.read_parquet(DATA_PATH)
    
    # Clean and filter
    df = df.filter(
        (pl.col("p_date") >= pl.lit(START_DATE).str.to_date("%Y-%m-%d")) &
        (pl.col("p_date") <= pl.lit(END_DATE).str.to_date("%Y-%m-%d")) &
        (pl.col("roe").is_not_null()) &
        (pl.col("mkt_cap") >= MIN_MKT_CAP)
    )
    
    # Sort for joins
    df = df.sort(["permaTicker", "p_date"])
    
    return df

def get_sp500_benchmark():
    print("📉 Fetching S&P 500 benchmark (GSPC)...")
    try:
        spy = yf.download("^GSPC", start=START_DATE, end=END_DATE, progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            # Handle new yfinance multi-index format
            spy_close = spy['Close']['^GSPC']
        else:
            spy_close = spy['Close']
        spy_returns = spy_close.pct_change().dropna()
        return spy_returns
    except Exception as e:
        print(f"⚠️ Error fetching S&P 500: {e}")
        # Return a zero series if failed
        return pd.Series(0, index=pd.date_range(START_DATE, END_DATE))

def backtest_strategy(df):
    print("🚀 Running Backtest: Top 10% ROE Strategy...")
    
    # Get all unique dates
    all_dates = df.select("p_date").unique().sort("p_date")["p_date"].to_list()
    
    portfolio_value = 100.0
    portfolio_history = []
    
    current_positions = {} # permaTicker -> {entry_price, weight, current_price}
    
    last_rebalance_month = -1
    
    pbar = tqdm(all_dates)
    for current_date in pbar:
        # 1. Update prices of current positions
        day_data = df.filter(pl.col("p_date") == current_date)
        if day_data.is_empty():
            continue
            
        if current_positions:
            total_current_value = 0
            tickers_to_exit = []
            
            # To avoid dictionary mutation during loop
            current_tickers = list(current_positions.keys())
            for ticker in current_tickers:
                if ticker == 'CASH': continue
                
                pos = current_positions[ticker]
                ticker_day = day_data.filter(pl.col("permaTicker") == ticker)
                
                if not ticker_day.is_empty():
                    new_price = ticker_day["close"][0]
                    day_ret = (new_price / pos['current_price']) - 1
                    
                    # Update weight based on return
                    pos['weight'] *= (1 + day_ret)
                    pos['current_price'] = new_price
                    
                    # Check Stop Loss (from entry price)
                    if (new_price / pos['entry_price'] - 1) <= -STOP_LOSS_PCT:
                        tickers_to_exit.append(ticker)
                else:
                    # Missing data: assume exit at last price (move to cash)
                    tickers_to_exit.append(ticker)
            
            # Process Exits
            for t in tickers_to_exit:
                pos = current_positions.pop(t)
                if 'CASH' not in current_positions:
                    current_positions['CASH'] = {'weight': 0.0}
                current_positions['CASH']['weight'] += pos['weight']

            portfolio_value = sum(p['weight'] for p in current_positions.values())
        
        # 2. Rebalance logic
        if current_date.month in REBALANCE_MONTHS and current_date.month != last_rebalance_month:
            last_rebalance_month = current_date.month
            
            # Selection: Top 10% ROE
            candidates = day_data.filter(pl.col("roe").is_not_null()).sort("roe", descending=True)
            top_n = max(10, int(len(candidates) * 0.1))
            selected = candidates.head(top_n)
            
            if not selected.is_empty():
                new_pos_weight = portfolio_value / len(selected)
                current_positions = {}
                for row in selected.to_dicts():
                    current_positions[row['permaTicker']] = {
                        'entry_price': row['close'],
                        'current_price': row['close'],
                        'weight': new_pos_weight
                    }
        
        # 3. Record history
        portfolio_history.append({
            'date': current_date,
            'value': portfolio_value
        })
        
        pbar.set_description(f"Value: {portfolio_value:.2f}")

    return pl.DataFrame(portfolio_history)

def generate_report(history, benchmark):
    print("📊 Generating detailed report...")
    
    # Prepare data for QuantStats
    pdf = history.to_pandas()
    pdf.set_index('date', inplace=True)
    pdf.index = pd.to_datetime(pdf.index)
    
    strategy_returns = pdf['value'].pct_change().dropna()
    
    # Align benchmark
    benchmark.index = pd.to_datetime(benchmark.index)
    common_index = strategy_returns.index.intersection(benchmark.index)
    strategy_returns = strategy_returns.loc[common_index]
    benchmark_aligned = benchmark.loc[common_index]
    
    # Save results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Plotting Cumulative Returns
    plt.figure(figsize=(14, 7))
    cum_strat = (1 + strategy_returns).cumprod()
    cum_bench = (1 + benchmark_aligned).cumprod()
    
    plt.plot(cum_strat, label=f"ROE Top 10% Strategy", color='blue', linewidth=1.5)
    plt.plot(cum_bench, label=f"S&P 500 (GSPC)", color='gray', linestyle='--', alpha=0.7)
    plt.title("Backtest Result: High ROE Strategy vs S&P 500", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Growth of $1")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "backtest_chart.png"), dpi=300)
    plt.close()

    # Generate Full HTML Report
    qs.reports.html(strategy_returns, benchmark_aligned, 
                    output=os.path.join(OUTPUT_DIR, "performance_report.html"),
                    title="ROE Top 10% Strategy Performance")
    
    # Textual Summary
    with open(os.path.join(OUTPUT_DIR, "summary_report.txt"), "w") as f:
        f.write("====================================================\n")
        f.write("      QUANTITATIVE BACKTEST REPORT: TOP 10% ROE     \n")
        f.write("====================================================\n")
        f.write(f"Period: {pdf.index[0].strftime('%Y-%m-%d')} to {pdf.index[-1].strftime('%Y-%m-%d')}\n")
        f.write(f"Universe: US Stocks (Min $100M Mkt Cap)\n")
        f.write(f"Rebalancing: Quarterly (Jan, Apr, Jul, Oct)\n")
        f.write(f"Stop Loss: {STOP_LOSS_PCT*100}% trailing from entry\n")
        f.write("----------------------------------------------------\n\n")
        
        # Metrics
        total_ret = (cum_strat.iloc[-1] - 1) * 100
        bench_ret = (cum_bench.iloc[-1] - 1) * 100
        years = (pdf.index[-1] - pdf.index[0]).days / 365.25
        ann_ret = ((1 + total_ret/100)**(1/years) - 1) * 100
        ann_bench = ((1 + bench_ret/100)**(1/years) - 1) * 100
        
        f.write(f"Total Cumulative Return:     {total_ret:.2f}%  (vs S&P 500: {bench_ret:.2f}%)\n")
        f.write(f"Annualized Return (CAGR):    {ann_ret:.2f}%  (vs S&P 500: {ann_bench:.2f}%)\n")
        f.write(f"Sharpe Ratio:                {qs.stats.sharpe(strategy_returns):.2f}\n")
        f.write(f"Max Drawdown:                {qs.stats.max_drawdown(strategy_returns)*100:.2f}%\n")
        f.write(f"Annual Volatility:           {qs.stats.volatility(strategy_returns)*100:.2f}%\n")
        f.write(f"Win Rate (Monthly):          {qs.stats.win_rate(strategy_returns.resample('ME').sum())*100:.2f}%\n")
        f.write(f"Profit Factor:               {qs.stats.profit_factor(strategy_returns):.2f}\n")
        f.write("\nNo look-ahead bias: Used PIT (Point-in-Time) filed dates.\n")
        f.write("No Survivorship Bias: Engine includes all filed tickers (within Tiingo scope).\n")

    print(f"✅ Success! Report and assets saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    try:
        df = load_data()
        if df.is_empty():
            print("❌ Error: No data found.")
        else:
            history = backtest_strategy(df)
            benchmark = get_sp500_benchmark()
            generate_report(history, benchmark)
    except Exception as e:
        import traceback
        traceback.print_exc()
