# PLAN D'ACTION POUR DEMAIN (Phase 4 & Consolidation)

Ce document détaille les prochaines étapes logiques pour le SMID-SEC Data Engine une fois que l'aspiration des prix (Phase 3) sera physiquement terminée.

## 1. Clôture Définitive de la Phase 3 (Prix)
- **PRÉREQUIS :** S'assurer que le disque LaCie est bien monté sur `/Volumes/LaCie`. Sans cela, les scripts risquent de créer des dossiers locaux fantômes sur le SSD.
- **Vérification finale :** En arrivant demain, exécutez le script d'audit final (`/tmp/final_audit.py`) pour vous assurer que les 19 930 fichiers sont bien physiquement présents sur le disque LaCie, et que le registre affiche 0 dossiers en `"pending"`.
- **Sanity Check :** Ouvrir un échantillon de 5 fichiers CSV de prix au hasard dans Excel ou Pandas pour vérifier visuellement que les données OHLCV sont bien formatées et sans corruption.

## 2. Lancement de la Phase 4 (Fondamentaux SEC)
- **Objectif :** Télécharger la partie "bilancielle" des entreprises (Revenus, Net Income, Actifs, Dettes) via l'API XBRL de la SEC.
- **Source :** La route officielle de la SEC `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`.
- **Prérequis :** La Phase 2, heureusement terminée ce soir, a déjà récupéré tous les numéros `CIK` nécessaires dans le registre.
- **Développement :** Demandez à l'IA de créer le script `04_sec_fundamentals.py` qui devra :
  1. Lire les CIK valides depuis le `master_tracker.csv`.
  2. Aspirer les JSON bruts et originaux sur le LaCie (dans le futur dossier `storage/bronze/sec_facts/`).
  3. Gérer rigoureusement le *rate limit* de la SEC (maximum 10 requêtes par seconde) et renseigner un *User-Agent* conforme (Nom + Email, selon les règles de la SEC).

## 3. Préparation de la Phase 5 (Vers le Parquet / Gold)
- Une fois que les prix historiques et les faits fondamentaux seront confortablement stockés en format "Bronze" (brut, CSV/JSON) sur le LaCie, le système sera prêt pour le "raffinage".
- La prochaine grande étape de data science sera de consolider ces milliers de petits fichiers en formats compressés très performants (`.parquet`), optimisés pour des librairies ultra-rapides comme *Polars* ou *DuckDB*.

### 💡 Recommandation d'Agent IA pour demain :
Pour le développement du fichier `04_sec_fundamentals.py`, il est fortement conseillé de commencer la conversation avec **Gemini 3.1 Pro High (L'Architecte)**. Le format XBRL de la SEC étant complexe, ce modèle sera le plus adapté pour concevoir une architecture de parsing robuste avant de passer à l'exécution de masse.
