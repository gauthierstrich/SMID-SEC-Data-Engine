# MASTER_CONTEXT : SMID-SEC Data Engine (Full Repository)

Ce document est la source unique et intégrale de vérité pour le projet SMID-SEC Data Engine. Il fusionne les visions stratégique, technique, historique et opérationnelle.

---

## 1. VISION STRATÉGIQUE & PILIERS
Le **SMID-SEC Data Engine** est conçu pour alimenter des modèles de trading quantitatif à haute performance. Contrairement aux approches "retail", ce système est bâti sur trois piliers de qualité institutionnelle :

*   **Zéro Biais de Survie (Survivorship-Bias Free) :** Capture systématique des entreprises délistées ("Ghosts"). Tout ticker ayant existé doit être présent dans le dataset.
*   **Zéro Biais d'Anticipation (Look-ahead Bias Free) :** Alignement strict sur les dates de publication effectives.
*   **Intégrité Temporelle :** Séparation des prix bruts (pour la taille/Market Cap) et des prix ajustés (pour les rendements).

**Vision Finale :** Avoir un système capable de rejouer l'histoire boursière des 20 dernières années comme si vous y étiez, sans aucun biais.

---

## 2. PROTOCOLE DE DONNÉES (Standards de Qualité)

### Gestion des Prix (La Règle d'Or)
*   `Close` (Unadjusted) : Utilisé **UNIQUEMENT** pour calculer la Market Cap (`Close * Shares Outstanding`).
*   `AdjClose` (Adjusted) : Utilisé **UNIQUEMENT** pour calculer les rendements et les performances via l'intégration des dividendes et splits.

### Persistence & Robustesse
*   **Atomicité :** Chaque téléchargement doit être atomique. Si un fichier est interrompu, il est considéré comme corrompu et doit être supprimé/repris.
*   **Source de Vérité :** Le `master_tracker.csv` est l'unique registre d'état. Aucun script ne doit "deviner" ; il consulte le registre.

### Validation des Données
*   **Prix Négatifs :** Interdits.
*   **Gaps Temporels :** Tout trou de plus de 5 jours de cotation doit être loggué pour investigation.

---

## 3. ARCHITECTURE TECHNIQUE & LOGISTIQUE

### Structure Hybride (SSD vs LaCie)
Le système exploite le différentiel de vitesse entre le SSD interne et le disque externe :
*   🚀 **SSD Interne (Performance & Logique)** : Héberge le code (`engine/core/`), les paramètres (`config/`), les logs et le registre (`registry/master_tracker.csv`).
*   📦 **Disque LaCie (Stockage de Masse)** : Dossier `/Volumes/LaCie/SMID-SEC Data Engine/storage/` pour les données RAW (Bronze), nettoyées (Silver) et les datasets finaux (Gold).

### Pile Technologique
*   **Hardware :** MacBook Air M3 (ARM64), 16 Go RAM.
*   **Logiciel :** Python / Pandas. 
*   **Optimisation :** Transition prévue vers **Polars** ou **DuckDB** pour le traitement multi-threadé natif sur M3.
*   **API :** Tiingo Professional (Source primaire).

---

## 4. HISTORIQUE DU DÉVELOPPEMENT & DÉCISIONS CLÉS

### Session 2026-03-19 : Initialisation
*   **Pivot Total :** Abandon de l'ancienne structure hybride (SEC/Yahoo) pour une source unique **100% Tiingo Professional API**.
*   **Optimisation M3 :** Conception "Memory Efficient" par chunks.

### Session 2026-03-22 : Bootstrap & Audit
*   **Phase 1 (Success) :** Extraction de **19 930 tickers** via `fundamentals/meta` de Tiingo.
*   **Audit CRITIQUE :** Identification que le plan Tiingo Power ($30) restreint les métadonnées de fondamentaux (secteurs, CIK) aux Dow 30, marquant l'univers SMID comme "non disponible".
*   **Vérification "Ghosts" :** Confirmation que les prix historiques des délistés (ex: TWTR, CELG) sont bien accessibles avec le plan actuel, sauvant la stratégie de "Biais de Survie".
*   **Pivot Phase 2 :** Décision de récupérer les métadonnées (Secteurs/CIK) via des sources gratuites (SEC EDGAR) tout en gardant Tiingo pour les prix OHLCV.

### Session 2026-03-22 (Soir) : Concurrence & Audit "Pas de Triche"
*   **Correction Race Condition :** Implémentation d'une fusion atomique (`df.update()`) au lieu d'un écrasement total (`df.to_csv()`) dans `02_sec_mirror.py` et `03_price_vacuum.py`. Exécution 100% parallèle sécurisée.
*   **Phase 2 (Terminée) :** Enrichissement SEC complété à 100% (Secteurs, Industries, CIK). Identification et marquage étanche des "Ghosts".
*   **Audit d'Intégrité ("Pas de Triche") :** Découverte de processus clonés (3 instances de l'aspirateur en conflit) ayant généré 1 973 faux succès dans le registre (données absentes physiquement).
*   **Remédiation Stricte :** Purge des processus isolés et rétrogradation des 1 973 tickers fantômes en `pending`, assurant un alignement mathématique parfait entre le registre et le stockage LaCie. Sprint final de la Phase 3 isolé.

### Session 2026-03-26 : Re-synchronisation & Reprise
*   **Santé du Stockage :** Confirmation que le disque LaCie est correctement monté sur `/Volumes/LaCie`.
*   **Inventaire Physique :** Présence de **12 872 fichiers OHLCV** valides dans `bronze/prices`.
*   **Désynchronisation Registre :** Détection de 224 fichiers physiques non encore validés dans le `master_tracker.csv` (12 648 `success` enregistrés).
*   **Status Phase 3 :** Aspiration avancée ~92%. Environ 1 400 tickers restants en `pending` réel.

---

## 5. ROADMAP D'EXTRACTION

### Phase 1 : Le Registre (The Ledger) [✅ TERMINE]
*   Volume : 19 930 tickers identifiés.
*   Status : Identité de base et statut vital (`isActive`) sécurisés.

### Phase 2 : Identité & Taxonomie [🚧 PIVOT]
*   **Objectif :** Enrichir le registre avec Secteurs, Industries et CIK.
*   **Stratégie :** Utilisation de l'API Submissions de la SEC (Gratuit) pour extraire les codes SIC et CIK à partir des tickers.

### Phase 3 : Aspiration Massive (The Vacuum) [🚀 EN COURS]
*   **Données :** OHLCV (20+ ans), Splits, Dividendes.
*   **Dualité :** Extraction simultanée des prix bruts et ajustés.

### Phase 4 : Fondamentaux [🔜 FUTUR]
*   Extraction des bilans, comptes de résultat et cash-flows.

### Phase 5 : Certification [🔜 FUTUR]
*   Génération du dataset final au format Parquet.

---

## 6. STRATÉGIE DE PIVOT PHASE 2 (Secteurs & CIK)
Sans l'Add-on Fundamentals de Tiingo, nous adoptons la méthode suivante :
1.  **CIK Mapping :** Téléchargement du fichier `ticker.json` de la SEC qui contient la table de correspondance Ticker -> CIK.
2.  **Sectors (SIC) :** Utilisation du CIK pour interroger `https://data.sec.gov/submissions/CIK##########.json`. Ce fichier JSON contient le code SIC (Standard Industrial Classification) qui permet de déduire le secteur et l'industrie avec une précision réglementaire.

---

## 7. INFRASTRUCTURE DE MIRRORING SEC (Alternative Fundamentals)
Pour contourner les limites d'abonnement Tiingo, le moteur utilise le système EDGAR de la SEC comme miroir de données.

### A. Récupération de l'Identité (CIK)
*   **Source :** `https://www.sec.gov/files/company_tickers.json`
*   **Fonctionnement :** Téléchargement périodique du mapping officiel Ticker <-> CIK.
*   **Stockage :** Cache local dans `engine/registry/sec_tickers.json`.

### B. Récupération de la Taxonomie (SIC & Secteurs)
*   **Source :** `https://data.sec.gov/submissions/CIK##########.json`
*   **Donnée extraite :** Le code **SIC** (Standard Industrial Classification).
*   **Mapping :** Un dictionnaire interne convertit les codes SIC (4 chiffres) en Secteurs/Industries lisibles pour le filtrage SMID.

### C. Récupération des Fondamentaux (XBRL FACTS)
*   **Source :** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
*   **Contenu :** Historique complet de tous les concepts XBRL déclarés (Revenus, Bénéfice Net, Actifs, Dettes).
*   **Infrastructure de Stockage :**
    *   **Bronze :** JSONs bruts sauvegardés sur LaCie (`storage/bronze/sec_facts/`).
    *   **Silver :** Extraction des "Core Metrics" standardisés (Net Income, Revenues, etc.) vers des fichiers Parquet.

### D. Contraintes de l'Infrastructure SEC
*   **User-Agent obligatoire :** Le script doit s'identifier (Nom + Email) pour respecter la politique de la SEC.
*   **Rate-Limit :** Maximum 10 requêtes par seconde (beaucoup plus rapide que Tiingo pour les métadonnées).

---
**Note à l'attention des Agents IA :** Ce document contient tout le nécessaire pour comprendre la philosophie et l'état du projet. Ne jamais simplifier à outrance : la rigueur de la donnée prime sur tout.
