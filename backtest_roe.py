import polars as pl
import os
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm

# --- CONFIGURATION ---
MATRIX_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"
INITIAL_CAPITAL = 100000
START_DATE = "2015-01-01"
END_DATE = "2026-04-01"
REBALANCE_FREQ = "3mo" # Tous les trimestres
TRANSACTION_FEE = 0.001 # 0.1% par transaction (Realism)

def run_backtest():
    print(f"🚀 Initialisation du Backtest ({START_DATE} au {END_DATE})...")
    
    # 1. Charger la Matrice (Lazy pour performance)
    df = pl.scan_parquet(MATRIX_PATH)
    
    # Filtrer la période et trier
    df = df.filter(
        (pl.col("p_date") >= datetime.strptime(START_DATE, "%Y-%m-%d").date()) &
        (pl.col("p_date") <= datetime.strptime(END_DATE, "%Y-%m-%d").date())
    ).sort("p_date")

    # 2. Identifier les dates de rebalancement
    # On prend toutes les dates de bourse dispo
    all_dates = df.select("p_date").unique().sort("p_date").collect().to_series().to_list()
    
    # On définit les paliers (rebalancement trimestriel)
    # Pour simplifier, on rebalance tous les 63 jours de bourse (~3 mois)
    rebalance_indices = list(range(0, len(all_dates), 63))
    
    current_capital = INITIAL_CAPITAL
    equity_curve = []
    portfolio = {} # {ticker: quantity}
    
    print(f"💰 Capital initial : {INITIAL_CAPITAL:,}$")
    print(f"🔄 Fréquence de rebalancement : {REBALANCE_FREQ}")

    # 3. Boucle de simulation temporelle
    for i in tqdm(range(len(all_dates)), desc="Simulation"):
        current_date = all_dates[i]
        
        # A. Mise à jour de la valeur du portefeuille quotidiennement
        if portfolio:
            # Récupérer les prix du jour pour nos tickers
            prices_today = df.filter(
                (pl.col("p_date") == current_date) & 
                (pl.col("ticker").is_in(list(portfolio.keys())))
            ).select(["ticker", "close"]).collect()
            
            # Calcul de la valeur totale actuelle (Cash + Actions)
            current_value = 0
            for row in prices_today.to_dicts():
                current_value += portfolio[row['ticker']] * row['close']
            
            # Si un ticker manque (faillite/delisting), sa valeur est 0 dans notre simulation
            # On ajoute le cash restant (normalement 0 ici si tout est investi)
            equity_curve.append({"date": current_date, "value": current_value})
            current_capital = current_value # Notre capital fluctue
        else:
            equity_curve.append({"date": current_date, "value": current_capital})

        # B. REBALANCEMENT (L'heure de l'ordre !)
        if i in rebalance_indices:
            # --- NOTRE HYPOTHÈSE (STRATÉGIE) ---
            # Objectif : Acheter les 10 boites avec le ROE le plus élevé
            # Filtres : Liquidité (ADV > 1M$) + Qualité (ROE > 15%)
            candidates = df.filter(
                (pl.col("p_date") == current_date) &
                (pl.col("adv_20d") > 1000000) &
                (pl.col("roe") > 0.15) &
                (pl.col("pe_ratio") < 25) # Pas trop cher
            ).sort("roe", descending=True).limit(10).collect()
            
            if not candidates.is_empty():
                # Vente de l'ancien portefeuille
                current_capital = current_capital * (1 - TRANSACTION_FEE) # Frais de sortie
                
                # Achat du nouveau
                num_stocks = len(candidates)
                cash_per_stock = current_capital / num_stocks
                
                portfolio = {}
                for row in candidates.to_dicts():
                    ticker = row['ticker']
                    price = row['close']
                    quantity = cash_per_stock / price
                    portfolio[ticker] = quantity
                
                # Frais d'entrée
                current_capital = current_capital * (1 - TRANSACTION_FEE)
                # print(f" - [{current_date}] Rebalancement : {num_stocks} actions achetées.")

    # 4. Rapport de Performance
    final_equity = pl.DataFrame(equity_curve)
    profit = final_equity['value'].tail(1)[0] - INITIAL_CAPITAL
    return_pct = (profit / INITIAL_CAPITAL) * 100
    
    print("\n--- [RAPPORT DE PERFORMANCE ALPHA] ---")
    print(f"🏁 Valeur finale : {final_equity['value'].tail(1)[0]:,.2f}$")
    print(f"📈 Profit Total : {profit:,.2f}$ ({return_pct:.2f}%)")
    
    # Calcul du Drawdown Maximum
    final_equity = final_equity.with_columns(
        pl.col("value").cum_max().alias("peak")
    ).with_columns(
        ((pl.col("value") - pl.col("peak")) / pl.col("peak")).alias("drawdown")
    )
    max_dd = final_equity["drawdown"].min() * 100
    print(f"📉 Drawdown Maximum : {max_dd:.2f}%")

    # 5. Graphique
    plt.figure(figsize=(12, 6))
    plt.plot(final_equity['date'], final_equity['value'], label="Stratégie High ROE / Low PE")
    plt.title("Évolution du Capital (Backtest 2015-2026)")
    plt.xlabel("Année")
    plt.ylabel("Valeur du Portefeuille ($)")
    plt.grid(True)
    plt.legend()
    plt.savefig("backtest_result.png")
    print(f"\n📊 Graphique de performance sauvegardé : backtest_result.png")

if __name__ == "__main__":
    run_backtest()
