# 📐 MÉTHODOLOGIE DE CALCUL : Le PER TTM (Trailing Twelve Months)

Ce document explique la logique mathématique utilisée par le SMID-SEC Data Engine pour calculer le ratio Cours/Bénéfice (P/E Ratio).

---

## 1. Pourquoi le PER "Simple" est-il trompeur ?

Dans notre version initiale, nous utilisions le PER "Spot" (Simple) :
**Formule :** `Prix du jour / Dernier bénéfice trimestriel publié`

### Les deux problèmes majeurs :
1. **Le biais de saisonnalité :** Une entreprise de jouets gagne 80% de son bénéfice au Q4 (Noël). Si on calcule son PER en été (basé sur le Q2), l'action aura l'air 10x plus chère qu'elle ne l'est réellement.
2. **Le saut de valeur :** À chaque publication de rapport, le dénominateur changeait brutalement (ex: passage d'un bénéfice trimestriel à un bénéfice annuel), créant des cassures artificielles dans tes graphiques.

---

## 2. La Solution Institutionnelle : Le TTM

Le **TTM (Trailing Twelve Months)** consiste à prendre la somme des bénéfices des **4 derniers trimestres** glissants. Cela permet d'avoir une vision de la capacité bénéficiaire de l'entreprise sur une année complète, quel que soit le moment de l'année.

**La formule actuelle de notre moteur :**
> **PER (TTM)** = (Prix Daily * Actions en circulation) / (Somme des Bénéfices des 4 derniers trimestres)

---

## 3. Logique d'implémentation (Anti-Triche)

Pour garantir un backtest sans "Look-ahead bias" (triche), le moteur suit ce processus rigoureux :

1. **Extraction CIK-Centric :** On identifie l'entreprise par son identifiant unique SEC (CIK).
2. **Normalisation des Flux :** Pour chaque nouveau rapport publié à la SEC (`filed_date`), le moteur récupère les données financières.
3. **Somme Glissante (Rolling Sum) :** On additionne le bénéfice actuel avec les 3 bénéfices trimestriels précédents.
4. **Calcul Quotidien (Daily Update) :** 
   - Le **Bénéfice TTM** (le dénominateur) reste fixe tant qu'un nouveau rapport n'est pas publié (pendant ~90 jours).
   - Le **Prix** (le numérateur) change chaque jour de bourse.
   - Le **PER TTM** est donc recalculé **chaque jour**, permettant d'identifier précisément le moment où une action entre dans ta zone d'achat (sous-évaluation).

---

## 4. Impact sur les Résultats

L'adoption du TTM a transformé la performance de la stratégie exemple :
*   **Performance PER Simple :** +25.45%
*   **Performance PER TTM :** **+318.84%**

**Conclusion :** Le lissage TTM élimine le "bruit" comptable et permet au modèle de se concentrer sur la **valeur intrinsèque réelle** de l'entreprise.

---
*Document de référence - SMID-SEC Data Engine*
