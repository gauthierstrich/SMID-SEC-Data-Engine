# AGENT_GUIDE : Stratégie de Routine IA

Ce document définit quel modèle d'IA utiliser pour chaque type de tâche afin d'optimiser le coût, la vitesse et la précision du projet.

---

## 🚀 1. Gemini 3.1 Pro High (L'Architecte)
**Quand l'utiliser :**
*   Conception de l'architecture globale (ex: passage de Pandas à Polars).
*   Résolution de bugs complexes liés aux biais (survivorship/look-ahead).
*   Ecriture de modules critiques (ex: le moteur de calcul du ROIC).
*   Audit de sécurité et optimisation de performance brute.

---

## ⚖️ 2. Gemini 3.1 Pro Low (L'Ingénieur)
**Quand l'utiliser :**
*   Développement de scripts standards (ex: `03_price_vacuum.py`).
*   Mises à jour de documentation et tenue du `DEVELOPMENT_LOG.md`.
*   Refactorisation de code existant pour plus de lisibilité.
*   Création de tests unitaires et de validation.

---

## ⚡ 3. Gemini 3 Flash (L'Exécuteur)
**Quand l'utiliser :**
*   Génération de boilerplate code simple.
*   Analyse rapide de logs d'erreurs (404/429).
*   Enrichissement de métadonnées simples via scripts.
*   Vérification de syntaxe ou formatage de fichiers.

---

## 🛠️ Instructions de Switch
Avant de commencer un nouveau module, l'agent actuel doit :
1. Consulter ce guide.
2. Recommander explicitement à l'utilisateur : *"Pour cette tâche de [Type], je vous suggère de passer sur [Modèle] pour garantir [Raison]."*
3. Fournir le fichier `MASTER_CONTEXT.md` à l'agent suivant pour une transition sans perte.
