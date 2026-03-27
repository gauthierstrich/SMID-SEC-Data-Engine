# 🧠 MEMORY : Progrès Technique & État du Système

Ce document est la mémoire vive et l'historique intégral du projet.

## 1. ÉTAT ACTUEL (27 Mars 2026)
- **Phase 1 (Le Registre) :** ✅ **100% Terminé.** 19 930 tickers identifiés.
- **Phase 2 (Identité & Taxonomie) :** ✅ **100% Terminé.** Enrichissement SEC complété (Secteurs, Industries, CIK).
- **Phase 3 (Aspiration Massive) :** 🚀 **~92% Terminé.**
    - Physique (LaCie) : **12 872 fichiers CSV.**
    - Registre : **12 648 validés.**
    - Reste : ~1 400 tickers en `pending`.
- **Phase 4 (Fondamentaux) :** 🔜 **Audit en cours.** Préparation du script `04_sec_fundamentals.py`.
- **Phase 5 (Certification) :** 🔜 **Futur.** Génération du dataset Parquet (Gold).

## 2. ARCHITECTURE TECHNIQUE & LOGISTIQUE

### Structure Hybride (M3 + LaCie)
- 🚀 **SSD Interne (Logique)** : Code (`engine/core/`), paramètres, logs et registre (`engine/registry/`).
- 📦 **Disque LaCie (Stockage)** : `/Volumes/LaCie/SMID-SEC Data Engine/storage/` pour Bronze, Silver et Gold.

### Pile Technologique
- **Hardware :** MacBook Air M3 (ARM64), 16 Go RAM.
- **Logiciel :** Python / Pandas. Transition prévue vers **Polars** ou **DuckDB**.
- **API :** Tiingo Professional (Prix) + SEC EDGAR (Métadonnées/Fondamentaux).
- **Git :** ✅ Dépôt privé GitHub `SMID-SEC-Data-Engine` (Utilisation de PAT).

## 3. HISTORIQUE DU DÉVELOPPEMENT & DÉCISIONS CLÉS

### Session 2026-03-19 : Initialisation
- Pivot total vers **100% Tiingo Professional API** pour les prix.
- Conception "Memory Efficient" par chunks.

### Session 2026-03-22 : Bootstrap & Audit
- Identification du bridage du plan Tiingo ($30) sur les secteurs/CIK (Dow 30 uniquement).
- Décision de pivot pour Phase 2 : Récupération métadonnées via **SEC EDGAR**.
- Sauvegarde de la stratégie "Ghosts" (prix historiques accessibles).

### Session 2026-03-22 (Soir) : Correction Criminelle
- Découverte de processus clonés ayant généré 1 973 faux succès.
- Remédiation : Rétrogradation forcée en `pending` pour alignement parfait registre/disque.
- Implémentation de `df.update()` pour la concurrence atomique.

### Session 2026-03-26/27 : Stabilisation & Git
- Audit de qualité : 100% de succès sur les fichiers extraits.
- Refactorisation pour **portabilité** (Mac/Linux) via chemins relatifs et `.env`.
- Première sauvegarde sécurisée sur GitHub.

## 4. INFRASTRUCTURE DE MIRRORING SEC
Pour contourner les limites Tiingo, le moteur utilise EDGAR :
- **CIK Mapping :** Table officielle Ticker <-> CIK castée localement dans `sec_tickers.json`.
- **Taxonomie :** Codes SIC convertis en secteurs/industries via submissions JSON.
- **XBRL Facts :** Aspiration des revenus/actifs vers `storage/bronze/sec_facts/`.

---
*Dernière mise à jour par l'agent : 2026-03-27*
