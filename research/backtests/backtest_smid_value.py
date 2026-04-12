import polars as pl
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Configuration des chemins
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
ALPHA_MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

def run_backtest():
    print("📈 Démarrage du Backtest: SMID Sector-Relative Value (10-15 Positions)...")
    
    if not os.path.exists(ALPHA_MATRIX_PATH):
        print(f"❌ Erreur: Matrice Alpha introuvable à {ALPHA_MATRIX_PATH}")
        return

    # 1. Chargement des données (Scan pour optimiser la mémoire)
    df = pl.scan_parquet(ALPHA_MATRIX_PATH)
    
    # 2. Nettoyage de base & Définition stricte de l'univers SMID Cap (300M$ - 10B$)
    df = df.filter(
        (pl.col("pe_ratio") > 0) & 
        (pl.col("mkt_cap") >= 300_000_000) & 
        (pl.col("mkt_cap") <= 10_000_000_000) & 
        (pl.col("sector") != "Unknown") &
        (pl.col("sector") != "Field not available for free/evaluation")
    )
    
    # 3. Calcul de la Médiane Sectorielle par jour (Relative Value)
    print("🔍 Calcul des médianes sectorielles quotidiennes...")
    df_with_median = df.with_columns(
        pl.col("pe_ratio").median().over(["p_date", "sector"]).alias("sector_pe_median")
    ).with_columns(
        (pl.col("pe_ratio") / pl.col("sector_pe_median")).alias("pe_relative_score")
    )
    
    # Collecte en mémoire (On a besoin de l'ordre temporel pour le rebalancement)
    full_data = df_with_median.collect().sort("p_date")
    
    all_dates = sorted(full_data["p_date"].unique().to_list())
    if not all_dates:
        print("❌ Aucune donnée valide trouvée pour le backtest.")
        return

    # Paramètres de simulation
    start_date = datetime(2015, 1, 1).date()
    end_date = all_dates[-1]
    rebalance_days = 126 # ~6 mois (252 jours de bourse / 2)
    max_positions = 15
    capital = 800.0
    equity_curve = []
    current_portfolio = [] # List of tickers/CIKs currently held
    
    current_date_idx = 0
    # On se place à la première date disponible après 2015
    while current_date_idx < len(all_dates) and all_dates[current_date_idx] < start_date:
        current_date_idx += 1
    
    print(f"🚀 Simulation de {all_dates[current_date_idx]} à {end_date}")

    portfolio_value = capital
    history = []

    while current_date_idx < len(all_dates):
        today = all_dates[current_date_idx]
        
        # --- PHASE DE SÉLECTION (REBALANCEMENT) ---
        # Filtres: PE < 80% mediane ET Croissance > 0
        candidates = full_data.filter(
            (pl.col("p_date") == today) &
            (pl.col("pe_relative_score") < 0.8) &
            (pl.col("rev_growth_yoy") > 0)
        ).sort("pe_relative_score") # On prend les moins chers en premier
        
        selected = candidates.head(max_positions)
        
        if selected.is_empty():
            # Si aucune opportunité, on reste en cash pour cette période (ou on garde l'ancien si possible)
            # Pour simplifier, on avance d'un jour jusqu'à trouver une opportunité
            current_date_idx += 1
            history.append({"date": today, "equity": portfolio_value, "positions": 0})
            continue

        num_pos = len(selected)
        cash_per_pos = portfolio_value / num_pos
        
        # On enregistre les prix d'entrée (adjClose pour gérer les splits)
        portfolio_entry = selected.select(["ticker", "cik", "adjClose"]).to_dicts()
        
        # --- PHASE DE DÉTENTION (6 MOIS) ---
        target_idx = min(current_date_idx + rebalance_days, len(all_dates) - 1)
        target_date = all_dates[target_idx]
        
        # On calcule le rendement de chaque ligne
        period_return = 0
        trade_details = []
        for pos in portfolio_entry:
            # Prix de sortie à 6 mois (Correction: on matche par TICKER, pas seulement par CIK)
            exit_data = full_data.filter(
                (pl.col("ticker") == pos["ticker"]) & 
                (pl.col("p_date") <= target_date)
            ).sort("p_date", descending=True).limit(1)
            
            if not exit_data.is_empty():
                price_exit = exit_data["adjClose"][0]
                ticker = exit_data["ticker"][0]
                raw_ret = (price_exit / pos["adjClose"]) - 1
                
                # Alerte si rendement suspect (> 200% en 6 mois)
                if raw_ret > 2.0:
                    print(f"  ⚠️ OUTLIER: {ticker} | Entry: {pos['adjClose']:.4f} | Exit: {price_exit:.4f} | Ret: {raw_ret*100:.1f}%")

                # Suppression du "plancher" Stop Loss irréaliste qui coupait magiquement les pertes à -20%.
                # On assume le rendement réel de la période.
                actual_ret = raw_ret
                
                final_ret = actual_ret - 0.003
                gain = (cash_per_pos * (1 + final_ret))
                period_return += gain
                trade_details.append({"ticker": ticker, "ret": actual_ret})
            else:
                period_return += 0 

        # Mise à jour du capital
        portfolio_value = period_return
        
        print(f"📅 {today} -> {target_date} | Equity: {portfolio_value:.2f}$ | Pos: {num_pos}")
        
        # Enregistrement historique (On remplit les jours intermédiaires pour le graph)
        for i in range(current_date_idx, target_idx + 1):
            history.append({"date": all_dates[i], "equity": portfolio_value, "positions": num_pos})
            
        current_date_idx = target_idx + 1

    # 4. Visualisation
    if not history:
        print("❌ Erreur: Historique vide.")
        return

    hist_df = pl.DataFrame(history)
    
    plt.figure(figsize=(12, 6))
    plt.plot(hist_df["date"], hist_df["equity"], label="SMID Value Recovery (800$ Start)", color='forestgreen', linewidth=2)
    plt.axhline(y=800, color='red', linestyle='--', alpha=0.5, label="Capital Initial")
    plt.title("Backtest : Stratégie SMID Value Relative (2015-2026)")
    plt.xlabel("Année")
    plt.ylabel("Valeur du Portefeuille ($)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plot_path = os.path.join(os.getcwd(), "backtest_smid_value.png")
    plt.savefig(plot_path)
    print(f"📊 Graphique sauvegardé: {plot_path}")
    
    # Statistiques Finales
    final_equity = hist_df["equity"].tail(1)[0]
    total_return = (final_equity / 800 - 1) * 100
    print(f"\n🏁 RÉSULTATS FINAUX :")
    print(f"💰 Capital Final : {final_equity:.2f}$")
    print(f"📈 Rendement Total : {total_return:.2f}%")

if __name__ == "__main__":
    run_backtest()
