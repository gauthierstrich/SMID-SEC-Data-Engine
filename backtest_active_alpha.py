import polars as pl
import os
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm

# --- CONFIGURATION ---
MATRIX_PATH = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/silver/alpha_matrix_master.parquet"
INITIAL_CAPITAL = 100000
START_DATE = "2012-01-01" # On commence en 2012 pour avoir assez de données de croissance (YoY)
END_DATE = "2026-04-01"
MAX_POSITIONS = 15
TRANSACTION_FEE = 0.001 
STOP_LOSS = -0.15 # Plus serré car on suit en daily

def run_active_value_backtest():
    print(f"🚀 Lancement du Moteur de Trading Actif ({START_DATE} au {END_DATE})...")
    
    # 1. Charger la Matrice (on ne garde que les colonnes nécessaires pour économiser la RAM)
    needed_cols = ["ticker", "p_date", "close", "pe_ratio", "rev_growth_yoy", "mkt_cap", "adv_20d", "roe", "long_term_debt", "short_term_debt", "equity"]
    df = pl.scan_parquet(MATRIX_PATH).select(needed_cols)
    
    # Calculer le ratio d'endettement à la volée
    df = df.with_columns(
        ((pl.col("long_term_debt").fill_null(0) + pl.col("short_term_debt").fill_null(0)) / pl.col("equity").replace(0, None)).alias("debt_to_equity")
    )
    
    df = df.filter(
        (pl.col("p_date") >= datetime.strptime(START_DATE, "%Y-%m-%d").date()) &
        (pl.col("p_date") <= datetime.strptime(END_DATE, "%Y-%m-%d").date())
    ).sort("p_date")

    all_dates = df.select("p_date").unique().sort("p_date").collect().to_series().to_list()
    
    current_cash = INITIAL_CAPITAL
    equity_curve = []
    portfolio = {} # {ticker: {'qty': Q, 'entry_price': P}}
    
    print(f"💰 Capital de départ : {INITIAL_CAPITAL:,}$")
    print(f"🛠️ Stratégie : Arbitrage PER Daily + Croissance Revenue > 0")

    # 3. Boucle de Trading Quotidienne
    for i in tqdm(range(len(all_dates)), desc="Trading"):
        current_date = all_dates[i]
        
        # A. On récupère les données du jour pour tout le marché SMID
        # Univers : Small/Mid Caps avec liquidité
        day_data = df.filter(
            (pl.col("p_date") == current_date) &
            (pl.col("mkt_cap").is_between(200e6, 3e9)) &
            (pl.col("adv_20d") > 500000)
        ).collect()
        
        if day_data.is_empty():
            continue

        # Calcul de la "Température du Marché" (PER Moyen)
        mean_pe = day_data.filter(pl.col("pe_ratio") > 0)["pe_ratio"].mean()
        if mean_pe is None: mean_pe = 15.0 # Fallback

        # B. GESTION DU PORTEFEUILLE ACTUEL (Ventes)
        current_portfolio_value = 0
        tickers_to_sell = []
        
        if portfolio:
            # On cherche les prix et ratios du jour pour nos actions
            today_stats = day_data.filter(pl.col("ticker").is_in(list(portfolio.keys())))
            stats_dict = {row['ticker']: row for row in today_stats.to_dicts()}
            
            for ticker, data in list(portfolio.items()):
                stats = stats_dict.get(ticker)
                
                if not stats: # Faillite ou Delisting (Sortie du dataset)
                    # print(f"💀 Faillite/Delist détecté sur {ticker}")
                    continue
                
                current_price = stats['close']
                current_pe = stats['pe_ratio']
                line_value = data['qty'] * current_price
                current_portfolio_value += line_value
                
                # CONDITION DE VENTE 1 : PER > Moyenne Marché
                if current_pe and current_pe > mean_pe:
                    tickers_to_sell.append(ticker)
                
                # CONDITION DE VENTE 2 : Stop Loss
                elif (current_price / data['entry_price'] - 1) < STOP_LOSS:
                    tickers_to_sell.append(ticker)

            # Exécution des ventes
            for ticker in tickers_to_sell:
                price = stats_dict[ticker]['close']
                cash_from_sale = portfolio[ticker]['qty'] * price * (1 - TRANSACTION_FEE)
                current_cash += cash_from_sale
                current_portfolio_value -= (portfolio[ticker]['qty'] * price)
                del portfolio[ticker]

        # C. GESTION DES OPPORTUNITÉS (Achats)
        slots_available = MAX_POSITIONS - len(portfolio)
        
        if slots_available > 0:
            # On cherche les meilleures opportunités selon tes critères
            candidates = day_data.filter(
                (pl.col("pe_ratio") > 0) & 
                (pl.col("pe_ratio") < (mean_pe * 0.7)) & # On veut un rabais de 30% vs le marché
                (pl.col("rev_growth_yoy") > 0.05) &      # Croissance > 5% (Sécurité)
                (pl.col("roe") > 0.05) &                 # Rentable
                (~pl.col("ticker").is_in(list(portfolio.keys()))) # Pas déjà en portefeuille
            ).sort("pe_ratio").limit(slots_available)
            
            if not candidates.is_empty():
                # On divise le cash dispo équitablement
                cash_per_pos = current_cash / slots_available
                
                for row in candidates.to_dicts():
                    ticker = row['ticker']
                    price = row['close']
                    qty = (cash_per_pos * (1 - TRANSACTION_FEE)) / price
                    portfolio[ticker] = {'qty': qty, 'entry_price': price}
                    current_cash -= (qty * price)

        # D. Enregistrement de l'Equity
        equity_curve.append({
            "date": current_date, 
            "value": current_portfolio_value + current_cash
        })

    # 4. Rapport de Performance
    final_df = pl.DataFrame(equity_curve)
    final_val = final_df['value'].tail(1)[0]
    profit_pct = (final_val / INITIAL_CAPITAL - 1) * 100
    
    print("\n--- [RAPPORT DE TRADING ACTIF ALPHA] ---")
    print(f"💰 Capital Final : {final_val:,.2f}$")
    print(f"📈 Performance Totale : {profit_pct:.2f}%")
    
    # Drawdown
    final_df = final_df.with_columns(pl.col("value").cum_max().alias("peak"))
    final_df = final_df.with_columns(((pl.col("value") - pl.col("peak")) / pl.col("peak")).alias("drawdown"))
    print(f"📉 Drawdown Max : {final_df['drawdown'].min()*100:.2f}%")

    # 5. Graphique
    plt.figure(figsize=(12, 6))
    plt.plot(final_df['date'], final_df['value'], color='navy', lw=1.5)
    plt.fill_between(final_df['date'], final_df['value'], INITIAL_CAPITAL, where=(final_df['value'] > INITIAL_CAPITAL), color='green', alpha=0.1)
    plt.title("Évolution du Capital - Stratégie Arbitrage PER + Croissance")
    plt.xlabel("Temps")
    plt.ylabel("Valeur ($)")
    plt.grid(True, alpha=0.3)
    plt.savefig("backtest_active_alpha.png")
    print(f"\n📊 Graphique de trading sauvegardé : backtest_active_alpha.png")

if __name__ == "__main__":
    run_active_value_backtest()
