# Stratégie de Mise à Jour Incrémentale Hebdomadaire (Hybride)

## 1. Objectif
Maintenir le dataset à jour chaque semaine en récupérant les prix et les fondamentaux via des sources gratuites, tout en préservant l'historique de haute qualité provenant de Tiingo dans un état "pur".

## 2. Architecture des Données (Isolation)
Les nouvelles données ne doivent jamais écraser les fichiers CSV originaux de Tiingo dans `storage/bronze/prices/`.

### Structure de stockage cible :
- `storage/bronze/prices_incremental/` : Contiendra les fichiers `.csv` récupérés via la méthode gratuite (ex: yfinance).
- `storage/bronze/fundamentals_incremental/` : Contiendra les derniers fichiers XBRL de la SEC non encore traités.

## 3. Flux de Travail Hebdomadaire (Prévu)

### Étape A : Détection des Gaps (Gap Scanner)
- Comparer la date la plus récente dans `prices_master.parquet` avec la date du jour.
- Générer une "Hit List" des jours manquants pour chaque ticker actif.

### Étape B : Acquisition des Prix (Incremental Price Puller)
- Source : `yfinance` ou API gratuite équivalente.
- Période : `start_date = Last_Tiingo_Date + 1 day`.
- Formatage : Mapper les colonnes pour correspondre au schéma interne (Date, Open, High, Low, Close, Volume, Adj Close).

### Étape C : Acquisition des Fondamentaux (SEC Delta)
- Utiliser le système de miroir SEC existant mais filtré sur les dates de soumission récentes.
- Détection des faillites : Analyser les dépôts de type `8-K` ou les absences prolongées de cotation pour marquer les entreprises comme "Ghosts".

### Étape D : Fusion Intelligente (Silver Integration)
- Dans la pipeline `05_silver_refinery.py`, lire les deux sources :
  ```python
  df_tiingo = pl.read_parquet("prices_master_tiingo.parquet")
  df_free = pl.read_csv("storage/bronze/prices_incremental/*.csv")
  df_final = pl.concat([df_tiingo, df_free]).unique(subset=["ticker", "date"])
  ```

## 4. Sécurité et Intégrité
- **Validation du Split :** Vérifier que les coefficients d'ajustement de la source gratuite sont cohérents avec ceux de Tiingo pour éviter des sauts de prix artificiels.
- **Audit de Faillite :** Si un ticker ne renvoie plus de données de prix, déclencher une vérification automatique sur le portail EDGAR de la SEC pour confirmer un retrait de la cote.

## 5. Prochaines Actions
1. Installer `yfinance`.
2. Créer le script `engine/pipeline/03b_incremental_price_vacuum.py`.
3. Mettre à jour l'orchestrateur pour inclure ce nouveau mode.
