# 🧠 MEMORY : Progrès Technique & État du Système

Ce document est la mémoire vive et historique du projet. Il enregistre les décisions techniques majeures, les sessions passées et l'état actuel de chaque phase.

## 1. ÉTAT ACTUEL DU SYSTÈME (27 Mars 2026)
- **Phase 1 (Registre) :** ✅ **100% Terminé.** 19 930 tickers identifiés.
- **Phase 2 (Métadonnées SEC) :** ✅ **100% Terminé.** Secteurs, CIK et Industries mappés via EDGAR.
- **Phase 3 (Prix OHLCV) :** 🚀 **92% Terminé.**
    - Physique (LaCie) : **12 872 fichiers CSV.**
    - Registre : **12 648 validés.** (224 orphelins à synchroniser).
    - À faire : ~1 400 tickers restants.
- **Phase 4 (Fondamentaux) :** 🔜 **Audit en cours.** Préparation du script `04_sec_fundamentals.py`.

## 2. INFRASTRUCTURE & BACKEND
- **Machine :** MacBook Air M3 (16 Go RAM).
- **Stockage :** Hybride SSD (Code/Registre) + LaCie (Stockage de masse `/Volumes/LaCie/`).
- **Git :** ✅ Repository GitHub Privé `SMID-SEC-Data-Engine` avec authentification PAT.
- **Portabilité :** Code refactorisé pour chemins relatifs (Compatible Mac/Linux).

## 3. HISTORIQUE DES SESSIONS CRITIQUES
- **2026-03-22 :** Découverte et correction de la *Race Condition* (perte de 1 973 fichiers). Implémentation du mode "Audit pas de triche". 
- **2026-03-26 :** Audit de qualité massif. Confirmation de l'intégrité à 100% des fichiers extraits malgré l'incident du disque débranché.
- **2026-03-27 :** Passage à Git et GitHub pour la synchronisation multi-serveurs.

## 4. DÉCISIONS TECHNIQUES MAJEURES
- **Pivot Source Unique :** Passage intégral à Tiingo Professional pour les prix (Abandon Yahoo).
- **Miroir SEC :** Utilisation gratuite de l'API SEC Submissions pour contourner les limites d'abonnement Tiingo sur les métadonnées universelles.
- **Format Bronze :** Utilisation du CSV pour le stockage brut par souci de lisibilité et de robustesse atomique. Format Parquet réservé pour les phases Silver/Gold.

---
*Dernière mise à jour par l'agent : 2026-03-27*
