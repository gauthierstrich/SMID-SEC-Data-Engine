# 🧠 QUANT MASTER PLAN : Rigueur Institutionnelle & Pipeline Alpha

Ce document définit les standards de qualité, les audits et la feuille de route pour transformer les données brutes en un dataset de backtest de qualité institutionnelle (type Hedge Fund Quantitatif).

La philosophie absolue : **Aucune triche, aucun biais du survivant, aucun biais d'anticipation (Look-ahead bias).**

---

## 🛡️ PHASE 1 : AUDIT D'EXHAUSTIVITÉ EXTRÊME (Le "Tiingo Squeeze")
*Objectif : Rentabiliser le mois d'abonnement Tiingo en s'assurant qu'AUCUNE entreprise historique n'a été oubliée.*

1. **Audit des Trous Temporels (Gaps) :**
   - *Test :* Scripter une vérification sur les 37 millions de lignes de prix pour s'assurer qu'il n'y a pas de jours de cotation manquants au milieu de la vie d'une entreprise.
   - *Test :* Vérifier les dates de début et de fin. Si une entreprise a fait faillite en 2018, avons-nous bien les prix jusqu'à son dernier jour de cotation ?
2. **Audit des Changements de Tickers (Corporate Actions) :**
   - *Test :* Valider que l'utilisation du `permaTicker` a bien permis de lier les historiques de prix sans cassure lorsqu'une entreprise a changé de nom ou de symbole (ex: FB -> META, ou fusions).
3. **Cross-Validation Tiingo vs SEC :**
   - *Test :* Comparer la liste de tous les CIK ayant publié un 10-K à la SEC dans les 15 dernières années avec notre `master_tracker.csv`. Si une entreprise a publié à la SEC mais n'a pas de prix chez Tiingo, il faut la ré-enquêter avant la fin de l'abonnement.
4. **Audit des "Penny/OTC/Ghosts" :**
   - *Test :* Confirmer que les 12 377 tickers inactifs dans notre registre couvrent bien les faillites majeures (Lehman Brothers, Enron, Blockbuster, Bed Bath & Beyond).

---

## 🧱 PHASE 2 : INTÉGRITÉ POINT-IN-TIME (PIT) & FONDAMENTAUX
*Objectif : Éradiquer le Look-Ahead Bias.*

1. **Validation du `filed_date` (Date de publication) :**
   - *Règle :* Dans le backtest, une donnée fondamentale (ex: Résultat Net de Q1) ne devient disponible pour le modèle qu'à la date de publication (`filed_date`), et NON à la date de fin de trimestre (`end_date`).
   - *Test :* Auditer la colonne `filed_date` dans `fundamentals_master.parquet` pour s'assurer qu'elle est toujours strictement supérieure à `end_date` (généralement +30 à +90 jours). Si `filed_date` est manquant, la donnée doit être rejetée.
2. **Gestion des "Restatements" (Corrections comptables SEC) :**
   - *Problème :* Les entreprises corrigent parfois leurs bilans passés. 
   - *Règle Quant :* Le modèle doit utiliser l'information *telle qu'elle était connue ce jour-là*, même si elle était fausse. Nous devons nous assurer que les données extraites sont bien celles déclarées initialement.
3. **Harmonisation Taxonomique Complète :**
   - *Action :* Étendre notre dictionnaire de tags SEC (qui en compte actuellement ~12) à ~40 tags pour capter toutes les subtilités comptables des banques, des assurances et des entreprises industrielles.

---

## ⚙️ PHASE 3 : FEATURE ENGINEERING (Les Signaux Alpha)
*Objectif : Construire les indicateurs mathématiques qui nourriront l'algorithme.*

Une fois l'audit réussi, nous calculerons les ratios suivants (de manière Point-In-Time) :

### A. Facteurs de Valeur (Value)
*   **P/E Ratio (Trailing & Forward) :** Prix / Bénéfice Net.
*   **P/B Ratio :** Prix / Valeur Comptable (Book Value).
*   **EV/EBITDA :** Valeur d'Entreprise / EBITDA.
*   **Free Cash Flow Yield :** FCF / Capitalisation Boursière.

### B. Facteurs de Qualité (Quality)
*   **ROE (Return on Equity) :** Résultat Net / Capitaux Propres.
*   **ROA (Return on Assets) :** Résultat Net / Total Actifs.
*   **Gross Margin :** Marge Brute.
*   **Debt-to-Equity :** Dette Totale / Capitaux Propres.
*   **Accruals :** (Résultat Net - Cash Flow Opérationnel) / Actifs (mesure la manipulation comptable).

### C. Facteurs de Momentum & Dynamique des Prix
*   **Momentum 1M, 3M, 6M, 12M :** Rendement du prix sur le passé.
*   **Volatilité 30j / 90j :** Écart-type des rendements quotidiens.

### D. Microstructure du Marché (Liquidité)
*   **ADV (Average Daily Volume) :** Volume moyen échangé en dollars (sur 20j).
*   **Amihud Illiquidity :** Mesure de l'impact sur le prix d'un volume donné.

---

## 🏆 PHASE 4 : GOLD LAYER & SIMULATION
*Objectif : Créer le panel de données final.*

*   **Structure du Gold Dataset :** Un tableau immense multi-indexé par `Date` et `Ticker`.
*   Pour chaque jour de bourse, la ligne contiendra le prix du jour ET les derniers fondamentaux connus exacts à ce jour (avec les ratios pré-calculés).
*   C'est ce fichier final qui sera injecté dans des librairies de backtest comme `Backtrader` ou `Vectorbt`.

---
*Créé par l'Agent Quant - 2026-04-05*
