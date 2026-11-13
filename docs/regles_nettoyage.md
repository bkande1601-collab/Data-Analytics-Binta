# Règles de nettoyage (générées automatiquement)

> Fichier généré par `python -m src.report_md` à partir de `docs/reports/cleaning_*.json`. Ne pas modifier à la main : relancer le pipeline.


## Membre 1 – `transaction.csv` (table de faits brute)

Lignes en entrée : **878 503** → en sortie : **878 503**

| # | Règle | Lignes concernées | Action | Justification métier |
|---|---|---:|---|---|
| 1 | conversion types numériques / code texte | 878 503 | float / string | calculs de CA et de volume |
| 2 | heures à millisecondes tronquées (formats hétérogènes) | 18 841 | complétées à 3 décimales + colonne datetime | permet de trier les tickets et d'analyser par heure |
| 3 | date/heure illisibles | 0 | ligne supprimée | sans date, la vente ne peut pas être comparée à N-1 |
| 4 | remise (Yes/No) -> booléen | 0 | valeurs inconnues = pas de remise | le prix vendu inclut déjà la remise ; on l'utilise pour mesurer l'effet promo |
| 5 | incohérence type (sale/return) vs signe de la quantité | 0 | type recalculé d'après le signe | le signe de la quantité fait foi |
| 6 | retours (quantité négative) | 461 | conservés, flag is_return ; qté retournée en positif à part | le CA 'net' = ventes - retours ; les ignorer surévaluerait le CA, les supprimer sans les compter aussi |
| 7 | quantité nulle/manquante ou prix <= 0 | 0 | ligne supprimée | ne représente aucune vente réelle |
| 8 | doublons stricts | 0 | 1re occurrence conservée | deux lignes identiques à la milliseconde = double scan, pas deux ventes |
| 9 | item_code absent de product.csv (orphelins) | 0 | ligne supprimée | sans catégorie la vente ne peut pas apparaître dans l'analyse par catégorie |
| 10 | quantités aberrantes (IQR x3.0 par article, ex. 160 kg en une ligne) | 5 374 | flag is_qty_outlier (conservées) | achats en gros possibles (restauration) : on signale, et on mesure leur poids dans le CA |
| 11 | prix de vente aberrants (IQR x3.0 par article) | 11 096 | flag is_price_outlier (conservées) | le prix peut réellement varier fortement (saison, remise) : on signale sans supprimer |

## Membre 2 – `product.csv` (référentiel produits / catégories)

Lignes en entrée : **251** → en sortie : **251**

| # | Règle | Lignes concernées | Action | Justification métier |
|---|---|---:|---|---|
| 1 | codes en texte | 251 | conversion en string | un code de 15 chiffres converti en float perdrait des chiffres et casserait les jointures |
| 2 | espaces parasites (item_name) | 6 | strip + espaces multiples réduits | évite qu'un même produit apparaisse sous deux écritures dans un filtre du dashboard |
| 3 | clé ou catégorie manquante | 0 | ligne supprimée | impossible de rattacher le produit à une transaction ou à une catégorie |
| 4 | doublons sur item_code | 0 | on garde la 1re occurrence | clé primaire de la dimension : un doublon multiplierait les ventes lors du JOIN |
| 5 | code catégorie avec plusieurs libellés | 0 | contrôle (aucune action si 0) | garantit une hiérarchie propre pour les graphiques par catégorie |
| 6 | noms de produit en double (codes différents) | 8 | item_label unique créé | deux articles distincts ne doivent pas être fusionnés mais doivent rester lisibles |
| 7 | traduction des catégories | 251 | colonne category_name_fr ajoutée | dashboard destiné au Comex francophone |

## Membre 3 – `price.csv` (prix de gros journaliers)

Lignes en entrée : **55 982** → en sortie : **55 982**

| # | Règle | Lignes concernées | Action | Justification métier |
|---|---|---:|---|---|
| 1 | dates invalides | 0 | ligne supprimée si non parsable | une date illisible ne peut pas être rattachée à une période de comparaison (N vs N-1) |
| 2 | prix manquant ou <= 0 | 0 | ligne supprimée | un coût d'achat nul ou négatif fausserait la marge ; on préfère ne pas calculer de marge |
| 3 | doublons (date, item_code) | 0 | moyenne des prix du jour | un seul prix de gros par article et par jour (clé de jointure unique) |
| 4 | prix de gros aberrants (IQR x3.0 par article) | 404 | flag is_price_outlier + prix corrigé (médiane de l'article) | un coût d'achat aberrant (0,01 ou 141 RMB/kg) ferait exploser ou s'effondrer la marge |

## Membre 4 – `loss_rate.csv` (taux de perte par article)

Lignes en entrée : **251** → en sortie : **251**

| # | Règle | Lignes concernées | Action | Justification métier |
|---|---|---:|---|---|
| 1 | BOM + code en texte | 251 | encodage utf-8-sig, code en string | le fichier commence par un caractère invisible (BOM) qui renommerait la 1re colonne |
| 2 | espaces parasites (item_name) | 6 | strip | cohérence avec product.csv |
| 3 | espace final dans le taux + conversion numérique | 251 | strip puis float | sans cela le taux reste du texte et aucune moyenne n'est possible |
| 4 | taux manquant ou illisible | 0 | laissé NaN ici ; imputé par la médiane de la catégorie à la consolidation (flag) | la médiane de catégorie est robuste aux valeurs extrêmes (consigne cours : médiane) |
| 5 | taux hors [0 ; 100] % | 0 | ligne supprimée | un pourcentage de perte ne peut pas sortir de cet intervalle |
| 6 | doublons sur item_code | 0 | 1re occurrence conservée | un seul taux de perte par article |
| 7 | valeurs aberrantes IQR x3.0 (bornes -0.5 - 19.8 %) | 8 | colonne is_loss_outlier (lignes conservées) | une perte très élevée est une information métier, pas une erreur de saisie |
| 8 | taux = 0 % | 22 | colonne is_zero_loss (conservé) | 0 % de perte sur un produit frais est suspect : à signaler au métier, pas à corriger seul |
