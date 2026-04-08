# 💎 SPÉCIFICATION TECHNIQUE : ALPHA MATRIX MASTER

Ce document est la référence absolue pour le fichier `silver/alpha_matrix_master.parquet`. Il définit la méthodologie de calcul de chaque signal Alpha.

---

## 🛡️ Principes Fondamentaux
1.  **Point-in-Time (PIT) :** Aucune donnée fondamentale n'est connue avant sa `filed_date` officielle à la SEC.
2.  **Survivorship-Bias Free :** Le dataset inclut les entreprises radiées (Delisted) pour éviter de surestimer les performances passées.
3.  **Normalisation :** Toutes les valeurs monétaires sont en USD. Les ratios sont exprimés en décimales (ex: 0.15 pour 15%).

---

## 📊 Dictionnaire des Colonnes

### 1. Identifiants & Contexte
| Colonne | Type | Description |
| :--- | :--- | :--- |
| `permaTicker` | String | Identifiant unique persistant (ex: `US000000002244`). |
| `ticker` | String | Symbole boursier (ex: `AAPL`). |
| `p_date` | Date | Date du jour de bourse (Format YYYY-MM-DD). |
| `sector` | String | Secteur d'activité officiel (Source SEC EDGAR). |
| `industry` | String | Industrie spécifique (Source SEC EDGAR). |

### 2. Signaux de Valeur (Value)
| Colonne | Formule | Description |
| :--- | :--- | :--- |
| `mkt_cap` | `Close * Shares Outstanding` | Capitalisation boursière du jour. |
| `pe_ratio` | `MktCap / Net Income` | Price-to-Earnings (Calculé de manière synthétique). |
| `pb_ratio` | `Close / (Equity / Shares)` | Price-to-Book. Valorisation vs Actifs Nets. |
| `ev_ebitda` | `(MktCap + Debt - Cash) / EBITDA` | Valeur d'Entreprise / EBITDA. |
| `fcf_yield` | `(OpCashFlow - Capex) / MktCap` | Rendement du Free Cash Flow. |

### 3. Signaux de Qualité (Quality)
| Colonne | Formule | Description |
| :--- | :--- | :--- |
| `roe` | `Net Income / Equity` | Return on Equity. Rentabilité des capitaux propres. |
| `roa` | `Net Income / Total Assets` | Return on Assets. Efficacité des actifs. |
| `gross_margin`| `(Revenue - COGS) / Revenue` | Marge brute. Pouvoir de prix de l'entreprise. |
| `debt_to_equity`| `Total Debt / Equity` | Ratio d'endettement. Mesure du risque financier. |
| `accruals` | `(NI - OpCashFlow) / Assets` | Mesure de la qualité des bénéfices (Earnings Quality). |

### 4. Signaux de Prix & Momentum
| Colonne | Fenêtre | Description |
| :--- | :--- | :--- |
| `mom_1m` | 21 jours | Rendement du prix sur le mois passé. |
| `mom_3m` | 63 jours | Rendement du prix sur le trimestre passé. |
| `mom_12m` | 252 jours | Rendement du prix sur l'année passée. |
| `vol_30d` | 30 jours | Écart-type glissant des rendements quotidiens. |
| `vol_90d` | 90 jours | Écart-type glissant des rendements quotidiens. |

### 5. Liquidité
| Colonne | Fenêtre | Description |
| :--- | :--- | :--- |
| `adv_20d` | 20 jours | **Average Daily Volume.** Moyenne du Volume * Prix. |

---
*Dernière révision : 5 Avril 2026*
