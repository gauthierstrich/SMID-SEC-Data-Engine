import polars as pl
import os
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm

# --- CONFIGURATION ---
MATRIX_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"
INITIAL_CAPITAL = 100000
START_DATE = "2010-01-01" # Plus long historique pour voir les cycles
END_DATE = "2026-04-01"
REBALANCE_DAYS = 126 # ~6 mois de bourse
TRANSACTION_FEE = 0.001 
STOP_LOSS = -0.20 # On coupe si une ligne perd 20%

def run_smid_value_backtest():
    print(f"🚀 Lancement du Backtest 'SMID Value Z-Score' ({START_DATE} au {END_DATE})...")
    
    # 1. Charger la Matrice
    df = pl.scan_parquet(MATRIX_PATH)
    
    # Filtrer la période et s'assurer que les colonnes vitales sont là
    df = df.filter(
        (pl.col("p_date") >= datetime.strptime(START_DATE, "%Y-%m-%d").date()) &
        (pl.col("p_date") <= datetime.strptime(END_DATE, "%Y-%m-%d").date())
    ).sort("p_date")

    all_dates = df.select("p_date").unique().sort("p_date").collect().to_series().to_list()
    rebalance_indices = list(range(0, len(all_dates), REBALANCE_DAYS))
    
    current_capital = INITIAL_CAPITAL
    equity_curve = []
    portfolio = {} # {ticker: {'qty': Q, 'entry_price': P}}
    
    for i in tqdm(range(len(all_dates)), desc="Simulation"):
        current_date = all_dates[i]
        
        # A. ÉVALUATION QUOTIDIENNE & STOP-LOSS
        if portfolio:
            prices_today = df.filter(
                (pl.col("p_date") == current_date) & 
                (pl.col("ticker").is_in(list(portfolio.keys())))
            ).select(["ticker", "close"]).collect()
            
            current_value = 0
            to_liquidate = []
            
            prices_dict = {row['ticker']: row['close'] for row in prices_today.to_dicts()}
            
            for ticker, data in portfolio.items():
                price = prices_dict.get(ticker, 0) # 0 si faillite/delist
                line_value = data['qty'] * price
                current_value += line_value
                
                # Check Stop-Loss
                if price > 0:
                    perf = (price / data['entry_price']) - 1
                    if perf < STOP_LOSS:
                        to_liquidate.append(ticker)
            
            # Gestion des sorties Stop-Loss (on transforme en cash pour le reste du semestre)
            for ticker in to_liquidate:
                cash_recovered = portfolio[ticker]['qty'] * prices_dict[ticker] * (1 - TRANSACTION_FEE)
                current_capital += cash_recovered
                del portfolio[ticker]
                # print(f" - [{current_date}] Stop-loss déclenché sur {ticker.upper()}")

            total_equity = current_value + current_capital
            equity_curve.append({"date": current_date, "value": total_equity})
        else:
            equity_curve.append({"date": current_date, "value": current_capital})

        # B. REBALANCEMENT (Tous les 6 mois)
        if i in rebalance_indices:
            # 1. Définir l'Univers SMID (MktCap entre 300M et 2B) avec PER valide
            universe = df.filter(
                (pl.col("p_date") == current_date) &
                (pl.col("mkt_cap").between(300e6, 2e9)) &
                (pl.col("pe_ratio").is_not_null()) &
                (pl.col("adv_20d") > 500000) # Minimum de liquidité
            ).collect()
            
            if not universe.is_empty():
                # 2. Normalisation Statistique du PER (Z-Score)
                # On calcule la moyenne et l'écart-type du PER à cet instant T
                mean_pe = universe["pe_ratio"].mean()
                std_pe = universe["pe_ratio"].std()
                
                # On sélectionne les entreprises dont le PER est < moyenne (Z-Score < 0)
                # Et on prend les 15 PER les plus bas (Deep Value)
                candidates = universe.filter(
                    (pl.col("pe_ratio") < mean_pe) & (pl.col("pe_ratio") > 0)
                ).sort("pe_ratio").limit(15)
                
                if not candidates.is_empty():
                    # Vendre tout l'existant
                    total_to_reinvest = current_value + current_capital
                    total_to_reinvest *= (1 - TRANSACTION_FEE)
                    
                    # Répartir le capital équitablement
                    cash_per_stock = total_to_reinvest / len(candidates)
                    portfolio = {}
                    current_capital = 0 # Tout est réinvesti
                    
                    for row in candidates.to_dicts():
                        qty = cash_per_stock / row['close']
                        portfolio[row['ticker']] = {
                            'qty': qty, 
                            'entry_price': row['close']
                        }

    # 4. Rapport et Graphique
    final_df = pl.DataFrame(equity_curve)
    profit_pct = (final_df['value'].tail(1)[0] / INITIAL_CAPITAL - 1) * 100
    
    print("\n--- [RÉSULTAT STRATÉGIE SMID VALUE Z-SCORE] ---")
    print(f"💰 Capital Final : {final_df['value'].tail(1)[0]:,.2f}$")
    print(f"📈 Performance Totale : {profit_pct:.2f}%")
    
    plt.figure(figsize=(12, 6))
    plt.plot(final_df['date'], final_df['value'], color='teal')
    plt.title(f"Backtest : Value SMID (Z-Score) + Stop Loss {STOP_LOSS*100}%")
    plt.xlabel("Années")
    plt.ylabel("Valeur Portefeuille ($)")
    plt.yscale('log') # Echelle log pour mieux voir la croissance
    plt.grid(True, which="both", ls="-")
    plt.savefig("backtest_smid_value.png")
    print(f"📊 Graphique sauvegardé : backtest_smid_value.png")

if __name__ == "__main__":
    run_smid_value_backtest()
