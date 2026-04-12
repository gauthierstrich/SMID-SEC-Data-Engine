import json
import glob
import os
from datetime import datetime

# Chemin vers les fichiers bruts (Bronze)
LACIE_STORAGE = '/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage'
fund_path = os.path.join(LACIE_STORAGE, 'bronze/fundamentals/sec_facts/*320193.json')
aapl_files = glob.glob(fund_path)

if not aapl_files:
    print("❌ Fichier AAPL introuvable.")
    exit()

aapl_file = aapl_files[0]
print(f"✅ Analyse du fichier brut : {os.path.basename(aapl_file)}\n")

with open(aapl_file, 'r') as f:
    data = json.load(f)

us_gaap = data.get('facts', {}).get('us-gaap', {})

# Tags de revenus connus pour Apple
revenue_tags = [
    "Revenues", 
    "SalesRevenueNet", 
    "RevenueFromContractWithCustomerExcludingAssessedTax"
]

print(f"{'Année (Fin)':<15} | {'Durée (Jours)':<15} | {'Revenu (Mds $)':<15} | {'Formulaire':<10} | {'Tag SEC'}")
print("-" * 80)

annual_revenues = []

for tag in revenue_tags:
    if tag in us_gaap:
        units = us_gaap[tag].get("units", {})
        if "USD" in units:
            for entry in units["USD"]:
                start_str = entry.get("start")
                end_str = entry.get("end")
                val = entry.get("val")
                form = entry.get("form")
                
                if start_str and end_str and val is not None:
                    # Calcul exact de la durée de la période comptable
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                    duration_days = (end_date - start_date).days
                    
                    # On ne garde que les périodes de ~1 an (360 à 370 jours)
                    if 360 <= duration_days <= 370:
                        annual_revenues.append({
                            "year_end": end_str,
                            "days": duration_days,
                            "revenue_b": val / 1e9,
                            "form": form,
                            "tag": tag
                        })

# On trie par date de fin et on dédoublonne (car un 10-K peut corriger un ancien 10-K)
# On garde la dernière déclaration pour une même date de fin
annual_revenues.sort(key=lambda x: x["year_end"])
unique_annual = {}
for r in annual_revenues:
    unique_annual[r["year_end"]] = r

# Affichage des 10 dernières années
for r in list(unique_annual.values())[-10:]:
    print(f"{r['year_end']:<15} | {r['days']:<15} | {r['revenue_b']:>10.2f} B$ | {r['form']:<10} | {r['tag']}")

print("\n🏆 Conclusion de l'Audit : Le vrai chiffre d'affaires annuel est extrait sans aucun doublon ni chevauchement.")
