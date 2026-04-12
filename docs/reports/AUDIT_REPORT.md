# 📑 RAPPORT D'AUDIT TECHNIQUE : "SMID-SEC DATA ENGINE" 
**Date :** Jeudi 9 Avril 2026  
**Statut :** OPÉRATIONNEL & SÉCURISÉ ✅

---

## 👨‍💻 SYNTHÈSE DES FAILLES CRITIQUES ET CORRECTIFS

Ce rapport détaille les interventions chirurgicales effectuées sur le moteur de récolte de données pour garantir une intégrité institutionnelle, l'absence de biais du survivant et une robustesse mathématique absolue.

### 1. 🛡️ BIAIS DU SURVIVANT (SURVIVORSHIP BIAS)
*   **Problème initial :** Le moteur ne voyait que les entreprises "vivantes" aujourd'hui. Les entreprises ayant fait faillite ou ayant été rachetées (les "fantômes") étaient ignorées par l'API Tiingo. Les erreurs 404 lors du téléchargement des prix n'étaient pas traitées comme des sorties de cote potentielles.
*   **Risque :** Un backtest artificiellement rentable car testé uniquement sur des gagnants (entreprises n'ayant pas fait faillite).
*   **Solution :** 
    *   Implémentation du **`permaTicker`** (ID permanent Tiingo invariant) au lieu du `ticker` recyclé pour toutes les requêtes de prix dans `03_price_vacuum.py`.
    *   Modification de la gestion des erreurs 404 pour préserver les métadonnées historiques sans les écraser.

### 2. 📈 RÉSILIENCE AUX SPLITS (CORPORATE ACTIONS)
*   **Problème initial :** La Capitalisation Boursière était calculée en multipliant le prix du jour (`close`) par le nombre d'actions (`shares outstanding`) de la SEC. Comme le chiffre SEC n'est mis à jour qu'une fois par trimestre, un split (ex: division du prix par 4) faisait s'effondrer la Market Cap de 75% artificiellement jusqu'à la publication suivante.
*   **Risque :** Faux signaux d'achat "Value" massifs lors de chaque split d'action.
*   **Solution :** Création d'un **`split_factor_proxy`** mathématique dynamique : `(close / adjClose)`. Ce facteur ajuste en temps réel le nombre d'actions au prorata du split détecté dans les prix ajustés. La Market Cap et les ratios P/E, P/B sont désormais stables et justes chaque jour.

### 3. 📐 INTÉGRITÉ DU "TRAILING TWELVE MONTHS" (TTM)
*   **Problème initial :** Le système "annualisait" les trimestres via un calcul de "Run-Rate" (Trimestre * 4), puis faisait une moyenne mobile sur 4 périodes. Ce mélange d'échelles temporelles créait des données aberrantes en cas de rapport manquant ou de saisonnalité forte.
*   **Risque :** Ratios financiers (ROE, ROA, PER) totalement déconnectés de la performance réelle de l'entreprise.
*   **Solution :** 
    *   **Refinery (05) :** Identification stricte des trimestres (90j) et des années (365j). Exclusion des périodes cumulatives (6m, 9m) polluantes.
    *   **Alpha Engine (06) :** Passage à une **Somme Roulante (Rolling Sum) Stricte** des 4 derniers trimestres "purs". Synchronisation automatique sur le rapport annuel (10-K) pour garantir la précision du TTM.

### 4. ⚙️ SYNCHRONISATION DE L'ORCHESTRATEUR (BUG FIX)
*   **Problème initial :** Une erreur de nomenclature dans `00_orchestrator.py` (`status_fundamentals_sec` au lieu de `status_fundamentals`) empêchait le système de savoir quand la phase SEC était terminée.
*   **Risque :** Loop infini de téléchargements et risque de bannissement d'IP par les serveurs de la SEC.
*   **Solution :** Resynchronisation totale des colonnes d'état entre tous les scripts du pipeline.

---

### 🚀 NOUVELLES MÉTRIQUES INSTITUTIONNELLES AJOUTÉES
Pour renforcer la capacité d'analyse SMID (Small/Mid Cap), les indicateurs suivants ont été injectés dans la matrice Alpha :
*   **Dette/Equity :** Évaluation de la structure financière.
*   **Enterprise Value (EV) :** Calculée via Market Cap + Dette Totale - Cash.
*   **EV/EBIT (TTM) :** Le standard "Deep Value" pour comparer les entreprises indépendamment de leur structure de capital.
*   **Free Cash Flow Yield (FCF Yield) :** Flux de trésorerie disponible réel (Op. Cash Flow - CapEx).

---

### 🏛️ GESTION DES SECTEURS (VALIDATION)
L'audit confirme que les secteurs et industries sont extraits **via la SEC** (Codes SIC) dans `02_sec_mirror.py` pour pallier les limitations de l'API Tiingo Free. La chaîne de transmission vers l'Alpha Engine est valide et fonctionnelle.

---
**Rapport généré par l'Auditeur Quantitatif.**
