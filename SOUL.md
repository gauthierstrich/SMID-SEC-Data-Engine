# 🕊️ SOUL : Vision & Philosophie du SMID-SEC Data Engine

Ce document définit l'essence, les valeurs et les standards non-négociables du projet. Tout agent travaillant sur ce système doit s'y conformer sans compromis.

## 1. LA MISSION SUPRÊME
Bâtir le dataset financier le plus pur et le plus robuste au monde pour l'univers **SMID (Small & Mid Caps)** américain. L'objectif final est de permettre la simulation parfaite de l'histoire boursière des 20 dernières années, comme si nous y étions en temps réel.

## 2. LES TROIS PILIERS DE QUALITÉ (Institutionnel-Grade)
1.  **Zéro Biais de Survie (Survivorship-Bias Free) :** Les "Ghosts" (entreprises délistées) sont aussi importants que les entreprises actives. Ils DOIVENT être présents pour éviter tout biais dans les tests de backtesting.
2.  **Zéro Biais d'Anticipation (Look-ahead Bias Free) :** Chaque donnée doit être strictement alignée sur sa date de publication effective.
3.  **Intégrité Temporelle :** Séparation stricte entre les prix bruts (calcul de Market Cap) et les prix ajustés (calcul de rendements).

## 3. LES RÈGLES D'OR DE L'INGÉNIERIE ("Pas de Triche")
*   **Atomicité :** Un téléchargement est soit réussi à 100%, soit supprimé. Jamais de fichiers tronqués.
*   **Alignement Mathématique :** Le registre (`master_tracker.csv`) doit être le miroir exact du stockage physique sur le disque LaCie. Toute désynchronisation est traitée comme une erreur critique.
*   **Audit Permanent :** Le système doit être capable de s'auto-auditer à tout moment pour vérifier la présence et la validité des fichiers.
*   **Efficacité M3 :** Le code est optimisé pour l'architecture ARM64 de MacBook M3 (Chunks, Parallélisation sécurisée).
*   **Protection des Secrets :** Jamais de clés API (`.env`) sur GitHub, même en dépôt privé. Utilisation systématisée de `.env.example`.

## 4. ÉTHIQUE DE LA DONNÉE
Nous ne cherchons pas la facilité. Si Tiingo n'a pas la donnée, nous allons la chercher à la source (SEC EDGAR). La rigueur de la donnée prime sur la vitesse de développement.

---
*"La donnée est le carburant de l'Alpha. Un carburant impur détruit le moteur."*
