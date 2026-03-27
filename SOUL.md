# 🕊️ SOUL : Vision & Philosophie du SMID-SEC Data Engine

Ce document définit l'essence, les valeurs et les standards non-négociables du projet.

## 1. LA MISSION SUPRÊME
Bâtir le dataset financier le plus pur et le plus robuste au monde pour l'univers **SMID (Small & Mid Caps)** américain. L'objectif final est de permettre la simulation parfaite de l'histoire boursière des 20 dernières années, comme si nous y étions en temps réel, sans aucun biais.

## 2. LES TROIS PILIERS DE QUALITÉ (Institutionnel-Grade)
1.  **Zéro Biais de Survie (Survivorship-Bias Free) :** Capture systématique des entreprises délistées ("Ghosts"). Tout ticker ayant existé doit être présent dans le dataset.
2.  **Zéro Biais d'Anticipation (Look-ahead Bias Free) :** Alignement strict sur les dates de publication effectives.
3.  **Intégrité Temporelle :** Séparation stricte entre les prix bruts (calcul de Market Cap) et les prix ajustés (calcul de rendements).

## 3. PROTOCOLE DE DONNÉES (Règles d'Or)

### Gestion des Prix
- **`Close` (Unadjusted) :** Utilisé **UNIQUEMENT** pour calculer la Market Cap (`Close * Shares Outstanding`).
- **`AdjClose` (Adjusted) :** Utilisé **UNIQUEMENT** pour calculer les rendements et les performances (Dividendes/Splits inclus).

### Persistence & Robustesse
- **Atomicité :** Chaque téléchargement doit être atomique. Si un fichier est interrompu, il est corrompu et doit être supprimé.
- **Source de Vérité :** Le `master_tracker.csv` est l'unique registre d'état. Aucun script ne doit "deviner".
- **Interdictions :** Prix négatifs interdits. Tout gap temporel > 5 jours doit être loggué pour investigation.

## 4. ÉTHIQUE & CONTRAINTES
- **Rigueur SEC :** Utilisation obligatoire du *User-Agent* conforme (Nom + Email) et respect du *Rate-Limit* (10 req/sec) pour EDGAR.
- **Priorité :** La rigueur de la donnée prime sur tout. Si Tiingo est limité, nous allons à la source (SEC).

---
*"La donnée est le carburant de l'Alpha. Un carburant impur détruit le moteur."*
