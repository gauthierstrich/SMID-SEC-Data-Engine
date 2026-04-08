# 🧠 CONTEXTE & GENÈSE DU PROJET : SMID-SEC Data Engine

Ce document définit l'essence, l'historique et la vision stratégique du moteur de données. Il consolide les anciennes archives (`SOUL`, `MEMORY`, `USER`).

---

## 🎯 1. La Mission
Bâtir le dataset financier le plus pur et le plus robuste au monde pour l'univers **SMID (Small & Mid Caps)** américain. L'objectif final est de permettre la simulation parfaite de l'histoire boursière, comme si nous y étions en temps réel, pour le développement de modèles de trading quantitatifs haute fidélité.

### Les Trois Piliers de Qualité (Institutionnel-Grade)
1.  **Zéro Biais de Survie (Survivorship-Bias Free) :** Capture systématique des entreprises délistées ("Ghosts"). L'audit final certifie la présence de 1 453 entreprises mortes dans la matrice de recherche.
2.  **Zéro Biais d'Anticipation (Look-ahead Bias Free) :** Alignement strict sur les dates de publication effectives (`filed_date`).
3.  **Qualité des Données :** Nettoyage algorithmique des anomalies comptables (Market Cap à 0, EPS nuls gérés par un P/E synthétique : MktCap/NetIncome).

---

## 📜 2. Historique du Développement & Défis Résolus

### Session Mars 2026 : La fondation
*   **Pivot Tiingo Professional & SEC :** Initialisation avec l'API Tiingo pour les prix historiques et la SEC pour les bilans (au format XBRL brut).

### Session Avril 2026 : La Guerre du Survivorship Bias
*   **Le Bug des "Fantômes" :** Découverte de milliers de tickers morts manquants. Aspiration de "Brute Force" via l'API Tiingo et l'historique de la SEC pour restaurer 1 500 "Fantômes".
*   **Le Pivot "CIK-Centric" :** Découverte d'une faille de jointure liée aux noms des Tickers (préfixes ajoutés par la SEC). Résolution via une extraction du CIK directement depuis le nom du fichier physique, garantissant 100% de matching.
*   **OOM (Out Of Memory) :** Gestion des crashs de RAM lors des jointures en utilisant un traitement séquentiel Ticker par Ticker avec PyArrow.

---

## 🕊️ 3. Philosophie de Données (Règles d'Or)
*   **L'Audit Physique est Loi :** Ne jamais faire confiance à un `status = success` sans vérifier le disque dur.
*   **Source de Vérité :** Le format Parquet est la vérité binaire finale.
*   **Performance :** Transition totale vers **Polars** pour des analyses instantanées sur 23 millions de lignes.

---

## 👤 4. Profil de l'Utilisateur
*   **Utilisateur :** Strich Gauthier.
*   **Style :** Focus extrême sur la rigueur mathématique et l'intégrité ("Pas de triche").

---
*"La donnée est le carburant de l'Alpha. Un carburant impur détruit le moteur."*
