# 🚀 PLAN D'ACTION : Finalisation du Moteur Alpha (Zéro Biais)

## 📍 ÉTAT ACTUEL (Fin de session du 5 Avril 2026)
*   **Dataset Bronze :** ✅ PHYSIQUEMENT COMPLET. 14 762 fichiers de prix et 7 329 archives SEC sont sur le disque LaCie.
*   **Anti-Biais :** 1 571 entreprises "Fantômes" (morts/faillites) ont été déterrées et téléchargées.
*   **Problème détecté :** La jointure par "Ticker" fait perdre des données car certains fichiers SEC utilisent des préfixes (ex: `nutx` au lieu de `UTX`).

---

## 🛠️ ÉTAPE 1 : Pivot vers l'Architecture "CIK-Centric"
L'objectif est de ne plus se fier au Ticker pour lier les prix et les fondamentaux, mais d'utiliser le **CIK** (identifiant unique immuable de la SEC).

1.  **Mettre à jour `05_silver_fundamentals_refinery.py` :**
    - S'assurer que le CIK est extrait de chaque nom de fichier JSON (format `TICKER_CIKXXXXXXXXXX.json`).
    - Sauvegarder `fundamentals_master.parquet` avec le CIK comme colonne de jointure principale.
2.  **Mettre à jour `06_alpha_engine.py` :**
    - Effectuer le `join_asof` en utilisant la colonne `cik` uniquement.
    - Cela garantira que 100% des fichiers JSON présents sur le disque finissent dans la matrice finale, même si le ticker est mal orthographié.

---

## 🧪 ÉTAPE 2 : Audit de Certification Finale
Une fois la matrice régénérée, lancer ce test Polars :
```python
import polars as pl
df = pl.read_parquet("silver/alpha_matrix_master.parquet")
print(f"Nombre de CIK uniques : {df['cik'].n_unique()}")
```
**Critère de succès :** Le nombre de CIK dans la matrice doit être égal au nombre de fichiers JSON sur le disque (~7 300).

---

## 📈 ÉTAPE 3 : Lancement du Premier Backtest
Maintenant que le dataset est **Institutional-Grade** (sans biais, sans triche, complet) :
1.  Utiliser la commande `python3 smid.py export` pour extraire un univers (ex: Secteur Technology, 2015-2025).
2.  Coder la stratégie (ex: Achat si ROE > 20% et PER < 15).
3.  Comparer les résultats avec un indice de référence (S&P 500).

---

## 📁 Rappel des Chemins
*   **Code :** `~/Bureau/SMID-SEC-Data-Engine/engine/pipeline/`
*   **Stockage :** `/media/gauthierstrich/LaCie/SMID-SEC-Data-Engine-Storage/`
*   **Dataset Maître :** `silver/alpha_matrix_master.parquet`

**Note de rigueur :** Ne jamais accepter un résultat de backtest si l'audit physique de l'Étape 2 n'est pas à 100%.
