# 🧠 CONTEXTE & GENÈSE DU PROJET : SMID-SEC Data Engine

Ce document définit l'essence, l'historique et la vision stratégique du moteur de données. Il consolide les anciennes archives (`SOUL`, `MEMORY`, `USER`).

---

## 🎯 1. La Mission
Bâtir le dataset financier le plus pur et le plus robuste au monde pour l'univers **SMID (Small & Mid Caps)** américain. L'objectif final est de permettre la simulation parfaite de l'histoire boursière, comme si nous y étions en temps réel, pour le développement de modèles de trading quantitatifs haute fidélité.

### Les Trois Piliers de Qualité (Institutionnel-Grade)
1.  **Zéro Biais de Survie (Survivorship-Bias Free) :** Capture systématique des entreprises délistées ("Ghosts"). Tout ticker ayant existé doit être présent.
2.  **Zéro Biais d'Anticipation (Look-ahead Bias Free) :** Alignement strict sur les dates de publication effectives (`filed_date`).
3.  **Intégrité Temporelle :** Séparation stricte entre les prix bruts (pour la Market Cap) et les prix ajustés (pour les rendements).

---

## 📜 2. Historique du Développement & Défis Résolus

### Session Mars 2026 : La fondation
*   **Pivot Tiingo Professional :** Initialisation avec l'API Tiingo pour les prix historiques.
*   **Audit Criminel :** Découverte de processus clonés ayant généré des faux succès. Remédiation par une rétrogradation forcée en `pending` et alignement physique rigoureux.
*   **Pivot SEC EDGAR :** Identification du bridage des données fondamentales sur Tiingo. Décision de basculer vers la source officielle (SEC) pour les CIK, les secteurs et les rapports XBRL.

### Session Avril 2026 : Le Raffinage (Silver Layer)
*   **Big Data Challenge :** Gestion des erreurs de mémoire (OOM) lors de la fusion de 13 000 CSV. Implémentation d'un système d'écriture incrémentale par chunks avec **Polars** et **PyArrow**.
*   **Matching CIK :** Résolution des problèmes de formatage (Float scientifique vs String) pour garantir une jointure parfaite entre Prix et Fondamentaux.
*   **Naissance de la Matrice Alpha :** Création du dataset `alpha_matrix_master.parquet` regroupant prix, secteurs et 20+ signaux quantitatifs quotidiens.

---

## 🕊️ 3. Philosophie de Données (Règles d'Or)
*   **La donnée prime sur tout :** Si une API est limitée, on remonte à la source brute.
*   **Source de Vérité :** Le `master_tracker.csv` est l'unique registre d'état.
*   **Performance :** Transition totale vers le format **Parquet** pour des analyses instantanées sur des millions de lignes.

---

## 👤 4. Profil de l'Utilisateur & Style
*   **Utilisateur :** Strich Gauthier.
*   **Style :** Focus extrême sur la rigueur mathématique et l'intégrité ("Pas de triche").
*   **Interaction :** Gère les agents IA comme une équipe d'ingénieurs qualifiés. Ne jamais simplifier à outrance, viser l'excellence institutionnelle.

---
*"La donnée est le carburant de l'Alpha. Un carburant impur détruit le moteur."*
