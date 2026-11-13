"""Transforme les rapports JSON de nettoyage (docs/reports) en un tableau Markdown lisible :
docs/regles_nettoyage.md  (chaque règle, nombre de lignes concernées, justification métier)."""
from __future__ import annotations

import json

from src.common import REPORTS, ROOT

ORDER = [("transaction", "Membre 1 – `transaction.csv` (table de faits brute)"),
         ("product", "Membre 2 – `product.csv` (référentiel produits / catégories)"),
         ("price", "Membre 3 – `price.csv` (prix de gros journaliers)"),
         ("loss_rate", "Membre 4 – `loss_rate.csv` (taux de perte par article)")]


def main() -> None:
    out = ["# Règles de nettoyage (générées automatiquement)\n",
           "> Fichier généré par `python -m src.report_md` à partir de `docs/reports/cleaning_*.json`. "
           "Ne pas modifier à la main : relancer le pipeline.\n"]
    for key, title in ORDER:
        rep = json.loads((REPORTS / f"cleaning_{key}.json").read_text(encoding="utf-8"))
        out.append(f"\n## {title}\n")
        out.append(f"Lignes en entrée : **{rep['lignes_entree']:,}** → en sortie : **{rep['lignes_sortie']:,}**\n".replace(",", " "))
        out.append("| # | Règle | Lignes concernées | Action | Justification métier |\n|---|---|---:|---|---|")
        for i, r in enumerate(rep["regles"], 1):
            n = f"{r['lignes_concernees']:,}".replace(",", " ")
            out.append(f"| {i} | {r['regle']} | {n} | {r['action']} | {r['justification_metier']} |")
    (ROOT / "docs" / "regles_nettoyage.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("docs/regles_nettoyage.md écrit")


if __name__ == "__main__":
    main()
