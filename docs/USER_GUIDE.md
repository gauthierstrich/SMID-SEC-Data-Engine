# 📖 GUIDE D'UTILISATION : SMID-SEC QUANT TERMINAL

Le terminal `smid.py` est l'interface de pilotage de ton infrastructure de données. Ce guide détaille les commandes disponibles pour la recherche et le backtesting.

---

## 🚦 Commandes de Base

### `status` : Vérifier la santé du moteur
Affiche les statistiques globales du dataset, la période couverte et le nombre d'entreprises chargées.
```bash
python3 smid.py status
```

### `get [TICKER]` : Explorer une action
Affiche les 10 derniers jours de données enrichies pour un ticker spécifique. Utile pour vérifier visuellement la cohérence des signaux.
```bash
python3 smid.py get NVDA
```

---

## 🎯 Recherche & Screening

### `screen` : Trouver des anomalies de marché
Permet de filtrer l'intégralité du marché à une date donnée selon des critères fondamentaux et techniques.

**Arguments disponibles :**
- `--date` : Date cible (Défaut : dernière date connue).
- `--pe-max` : Filtrer par valorisation attractive.
- `--roe-min` : Filtrer par haute rentabilité.
- `--mom-min` : Filtrer par momentum positif.
- `--sector` : Restreindre à un secteur SEC.

**Exemple :** Trouver les entreprises technologiques rentables avec un PER < 20 :
```bash
python3 smid.py screen --sector Technology --pe-max 20 --roe-min 0.15
```

---

## 📥 Préparation de Backtest

### `export` : Extraire un dataset allégé
C'est la commande la plus importante pour le développement. Elle génère un fichier Parquet sur mesure pour ton script de backtest.

**Pourquoi l'utiliser ?**
Au lieu de charger 40 Go de données, ton script de backtest ne chargera que quelques Mo, accélérant tes itérations de 100x.

**Arguments :**
- `--output` : Nom du fichier généré (obligatoire).
- `--start` / `--end` : Fenêtre temporelle du backtest.
- `--cols` : Liste des signaux nécessaires (ex: `pe_ratio,mom_12m`).
- `--min-adv` : Exclure les actions non liquides (ex: `--min-adv 1000000`).

**Exemple de flux de travail :**
1. J'exporte les données :
   ```bash
   python3 smid.py export --output my_strategy.parquet --start 2010-01-01 --cols pe_ratio,roe,mom_12m --min-adv 500000
   ```
2. Je code mon backtest en chargeant uniquement `my_strategy.parquet`.

---
*Développé pour la Finance Quantitative de Précision.*
