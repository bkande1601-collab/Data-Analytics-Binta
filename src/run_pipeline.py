"""Exécute toute la chaîne : bruts -> nettoyage (4 fichiers) -> modèle en étoile -> dashboard -> figures.

    python -m src.run_pipeline              # tout
    python -m src.run_pipeline --no-figures # sans les images
"""
from __future__ import annotations

import argparse
import sys

from src import build_dashboard, build_gold, clean_loss_rate, clean_price, clean_product, clean_transaction
from src.common import RAW


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()
    missing = [f for f in ("transaction.csv", "product.csv", "price.csv", "loss_rate.csv") if not (RAW / f).exists()]
    if missing:
        sys.exit(f"Fichiers manquants dans data/raw : {', '.join(missing)} (voir README, section 'Données').")

    # L'ordre compte : product d'abord (sert à contrôler les codes orphelins des transactions).
    for step in (clean_product, clean_loss_rate, clean_price, clean_transaction):
        step.main()
    build_gold.main()
    build_dashboard.main()
    from src import report_md
    report_md.main()
    if not args.no_figures:
        from src import make_figures
        make_figures.main()


if __name__ == "__main__":
    main()
