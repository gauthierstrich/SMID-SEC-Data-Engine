import polars as pl
import os
from dotenv import load_dotenv
import requests

load_dotenv()
API_KEY = os.getenv("TIINGO_API_KEY")
LACIE_STORAGE = os.getenv("LACIE_STORAGE_PATH", "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage")
FUND_PATH = os.path.join(LACIE_STORAGE, "silver/fundamentals_master.parquet")

def get_fresh_prices(ticker):
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?startDate=2010-01-01&token={API_KEY}"
    r = requests.get(url)
    return pl.DataFrame(r.json()).with_columns(pl.col("date").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("p_date"))

def run_audit(ticker, cik):
    print(f"\n🔍 AUDIT TECHNIQUE PROFOND : {ticker.upper()} (CIK: {cik})")
    
    # 1. Extraction des données
    prices = get_fresh_prices(ticker)
    funds = pl.read_parquet(FUND_PATH).filter(pl.col("cik") == cik)
    funds = funds.pivot(values="val", index=["filed_date"], on="tag", aggregate_function="last")
    funds = funds.with_columns(pl.col("filed_date").str.to_date("%Y-%m-%d").alias("f_date")).sort("f_date")

    # 2. Jointure Asof (Simulation Point-in-Time)
    df = prices.join_asof(funds, left_on="p_date", right_on="f_date")

    # 3. FORMULE QUANTE : Normalisation du Capital
    # On calcule les actions normalisées (en base adjClose actuelle)
    # Norm_Shares = (Close_Brut * Shares_SEC) / AdjClose_Brut
    df = df.with_columns([
        ((pl.col("close") * pl.col("shares_outstanding")) / pl.col("adjClose")).alias("norm_shares")
    ])
    
    # Forward-fill pour maintenir la continuité entre les rapports
    df = df.with_columns(pl.col("norm_shares").forward_fill().alias("norm_shares"))

    # Market Cap Finale = adjClose * norm_shares
    df = df.with_columns([
        (pl.col("adjClose") * pl.col("norm_shares")).alias("mkt_cap_quant")
    ])

    # 4. VÉRIFICATION DES SPLITS (STRESS TEST)
    # On cherche les jours où le prix brut (close) a bougé de plus de 20% (signe de split possible)
    # mais où la Market Cap calculée NE DOIT PAS avoir bougé.
    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1) - 1).alias("price_change"),
        (pl.col("mkt_cap_quant") / pl.col("mkt_cap_quant").shift(1) - 1).alias("mkt_cap_change")
    ])

    splits = df.filter(pl.col("price_change").abs() > 0.20)
    
    if splits.is_empty():
        print(f"✅ Aucun split majeur détecté pour {ticker} sur la période.")
    else:
        print(f"📊 {len(splits)} Splits détectés. Analyse de la stabilité...")
        for row in splits.to_dicts():
            date = row['p_date']
            p_chg = row['price_change'] * 100
            m_chg = row['mkt_cap_change'] * 100
            status = "✅ STABLE" if abs(m_chg) < 5 else "❌ ERREUR DE CALCUL"
            print(f"   📅 {date} | Split (Prix): {p_chg:+.1f}% | Impact Market Cap: {m_chg:+.2f}% | {status}")

    # 5. ÉCHANTILLONNAGE DE VÉRITÉ
    print("\n📈 Échantillons de valorisation (Point-in-Time) :")
    sample = df.filter(pl.col("p_date").dt.month() == 1).group_by(pl.col("p_date").dt.year()).agg(pl.all().last()).sort("p_date")
    print(sample.select(["p_date", "close", "adjClose", "shares_outstanding", "mkt_cap_quant"]))

if __name__ == "__main__":
    # Audit de NVIDIA (Split 10:1 en 2024)
    run_audit("nvda", "0001045810")
    # Audit de APPLE (Split 4:1 en 2020, 7:1 en 2014)
    run_audit("aapl", "0000320193")
