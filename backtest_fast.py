import polars as pl
import os
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm

# --- CONFIGURATION ---
MATRIX_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"
INITIAL_CAPITAL = 100000
START_DATE = "2012-01-01"
END_DATE = "2026-04-01"
MAX_POSITIONS = 20
TRANSACTION_FEE = 0.001 
STOP_LOSS = -0.25 # On laisse un peu plus de respiration

def run_fast_backtest():
    print(f"🚀 Chargement de la Matrice en RAM pour accélération maximale...")
    
    # 1. CHARGEMENT TOTAL EN RAM (Optimisation)
    # On ne prend que les colonnes vitales pour que ça tienne en RAM
    needed_cols = ["ticker", "p_date", "close", "pe_ratio", "rev_growth_yoy", "mkt_cap", "adv_20d", "roe"]
    
    # On charge tout le dataset d'un coup
    df = pl.read_parquet(MATRIX_PATH, columns=needed_cols)
    
    # Filtrage temporel
    df = df.filter(
        (pl.col("p_date") >= datetime.strptime(START_DATE, "%Y-%m-%d").date()) &
        (pl.col("p_date") <= datetime.strptime(END_DATE, "%Y-%m-%d").date())
    ).sort("p_date")

    all_dates = df.select("p_date").unique().sort("p_date")["p_date"].to_list()
    
    # Indexation par date pour un accès instantané (Vitesse ++)
    # On groupe par date une seule fois
    df_by_date = df.partition_by("p_date", as_dict=True)

    current_cash = INITIAL_CAPITAL
    equity_curve = []
    portfolio = {} # {ticker: {'qty': Q, 'entry_price': P}}
    
    print(f"💰 Capital : {INITIAL_CAPITAL:,}$ | {len(all_dates)} jours à simuler.")

    # 3. Boucle de Trading
    for current_date in tqdm(all_dates, desc="Trading"):
        day_data = df_by_date.get((current_date,))
        if day_data is None: continue

        # A. ÉVALUATION DU PORTEFEUILLE & VENTES
        current_portfolio_value = 0
        tickers_to_sell = []
        
        if portfolio:
            # Stats du jour pour nos actions (plus rapide via join ou filter)
            today_stats = day_data.filter(pl.col("ticker").is_in(list(portfolio.keys())))
            stats_dict = {row['ticker']: row for row in today_stats.to_dicts()}
            
            for ticker, data in list(portfolio.items()):
                stats = stats_dict.get(ticker)
                
                if not stats: # Delisté ou Faillite (Valeur 0)
                    continue
                
                price = stats['close']
                growth = stats['rev_growth_yoy']
                line_value = data['qty'] * price
                current_portfolio_value += line_value
                
                # --- TES NOUVELLES RÈGLES DE VENTE ---
                # 1. Vente si la croissance devient négative (Alerte Fondamentale)
                if growth is not None and growth < 0:
                    tickers_to_sell.append(ticker)
                
                # 2. Vente si Stop Loss atteint
                elif (price / data['entry_price'] - 1) < STOP_LOSS:
                    tickers_to_sell.append(ticker)

            # Exécution des ventes
            for ticker in tickers_to_sell:
                price = stats_dict[ticker]['close']
                current_cash += portfolio[ticker]['qty'] * price * (1 - TRANSACTION_FEE)
                current_portfolio_value -= (portfolio[ticker]['qty'] * price)
                del portfolio[ticker]

        # B. ACHATS (Si places disponibles)
        slots_available = MAX_POSITIONS - len(portfolio)
        if slots_available > 0 and current_cash > 100:
            # Univers : Small/Mid Caps Liquides
            # On cherche PER bas ET Croissance positive
            candidates = day_data.filter(
                (pl.col("mkt_cap").is_between(200e6, 3e9)) &
                (pl.col("adv_20d") > 1000000) &
                (pl.col("pe_ratio") > 2) & (pl.col("pe_ratio") < 12) & # Arbitrage Value
                (pl.col("rev_growth_yoy") > 0.10) & # On exige 10% de croissance pour acheter
                (~pl.col("ticker").is_in(list(portfolio.keys())))
            ).sort("pe_ratio").limit(slots_available)
            
            if not candidates.is_empty():
                cash_per_pos = current_cash / slots_available
                for row in candidates.to_dicts():
                    price = row['close']
                    qty = (cash_per_pos * (1 - TRANSACTION_FEE)) / price
                    portfolio[row['ticker']] = {'qty': qty, 'entry_price': price}
                    current_cash -= (qty * price)

        equity_curve.append({"date": current_date, "value": current_portfolio_value + current_cash})

    # 4. Résultats
    final_df = pl.DataFrame(equity_curve)
    final_val = final_df['value'].tail(1)[0]
    print(f"\n📈 Performance Totale : {(final_val/INITIAL_CAPITAL-1)*100:.2f}%")
    
    plt.figure(figsize=(12, 6))
    plt.plot(final_df['date'], final_df['value'], color='tab:blue')
    plt.title("Equity Curve - Strategy: Value Growth Hold")
    plt.grid(True, alpha=0.3)
    plt.savefig("backtest_optimized.png")
    print(f"📊 Graphique sauvegardé : backtest_optimized.png")

if __name__ == "__main__":
    run_fast_backtest()
