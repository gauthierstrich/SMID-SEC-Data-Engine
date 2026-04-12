import polars as pl
import os
from datetime import date

LACIE_STORAGE = "/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage"
MATRIX_PATH = os.path.join(LACIE_STORAGE, "silver/alpha_matrix_master.parquet")

def run_audit():
    print("🏦 EXAMEN DE CERTIFICATION - SMID DATA ENGINE v3.0\n")
    df = pl.scan_parquet(MATRIX_PATH)

    # --- TEST 1 : SURVIVORSHIP BIAS (Le cas Bed Bath & Beyond) ---
    print("🕵️ Test 1 : Biais du Survivant (Recherche de tickers délistés)...")
    bbby = df.filter(pl.col("ticker").str.to_lowercase() == "bbby").collect()
    if bbby.is_empty():
        print("❌ ÉCHEC : BBBY est absent. Le moteur souffre de biais du survivant.")
    else:
        last_date = bbby["p_date"].max()
        print(f"✅ SUCCÈS : BBBY présent jusqu'au {last_date}. Pas de biais de survie détecté.")

    # --- TEST 2 : LOOK-AHEAD BIAS (Évolution réelle du capital) ---
    print("\n🕵️ Test 2 : Biais d'Anticipation (Invariance du Capital)...")
    # Prenons un cas complexe : Un ticker présent sur 10 ans
    # On compare la Market Cap calculée avec la réalité historique connue.
    aapl = df.filter(pl.col("ticker").str.to_lowercase() == "aapl").collect().sort("p_date")
    
    # On regarde 2012 vs 2024
    cap_2012 = aapl.filter(pl.col("p_date").dt.year() == 2012).select("mkt_cap").mean()[0,0]
    cap_2024 = aapl.filter(pl.col("p_date").dt.year() == 2024).select("mkt_cap").mean()[0,0]
    
    # Réalité historique approximative : AAPL 2012 ~ 500B$ | 2024 ~ 3000B$
    print(f"   Apple Market Cap 2012 : {cap_2012/1e9:.1f}B$")
    print(f"   Apple Market Cap 2024 : {cap_2024/1e9:.1f}B$")
    
    if cap_2012 > 1000e9: # Si Apple affiche 1 Trillion en 2012, c'est qu'on a triché (on a utilisé les actions de 2024)
        print("❌ ÉCHEC : Market Cap passée surestimée. Biais d'anticipation détecté.")
    else:
        print("✅ SUCCÈS : La Market Cap historique semble réaliste.")

    # --- TEST 3 : SPLIT INTEGRITY (Zéro Trous) ---
    print("\n🕵️ Test 3 : Intégrité des Splits (NVDA June 2024)...")
    nvda = df.filter((pl.col("ticker").str.to_lowercase() == "nvda") & 
                     (pl.col("p_date") >= date(2024, 6, 5)) & 
                     (pl.col("p_date") <= date(2024, 6, 12))).collect()
    
    mkt_cap_pre = nvda.filter(pl.col("p_date") == date(2024, 6, 7))["mkt_cap"][0]
    mkt_cap_post = nvda.filter(pl.col("p_date") == date(2024, 6, 10))["mkt_cap"][0]
    deviation = abs(mkt_cap_post / mkt_cap_pre - 1) * 100
    
    print(f"   NVDA Pre-Split: {mkt_cap_pre/1e9:.1f}B$ | Post-Split: {mkt_cap_post/1e9:.1f}B$")
    if deviation < 5:
        print(f"✅ SUCCÈS : Déviation de {deviation:.2f}% lors du split. Continuité parfaite.")
    else:
        print(f"❌ ÉCHEC : Saut de valorisation de {deviation:.2f}% détecté.")

if __name__ == "__main__":
    run_audit()
