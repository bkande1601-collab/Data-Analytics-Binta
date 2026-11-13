"""Génère le dashboard interactif (un seul fichier HTML autonome, sans serveur ni connexion) :
    dashboard/dashboard.html  <- dashboard/template.html + données agrégées du modèle GOLD + Chart.js (vendor/).

Les données viennent uniquement de data/gold/*.csv (fact_ventes_jour committé), donc le dashboard se
régénère sans le gros fichier de transactions.
"""
from __future__ import annotations

import json

from src.common import GOLD, ROOT, pd

DASH = ROOT / "dashboard"
MONTHS_FR = ["Juil", "Août", "Sept", "Oct", "Nov", "Déc", "Janv", "Févr", "Mars", "Avr", "Mai", "Juin"]
MEASURES = ["revenue_net", "quantity_sold_kg", "gross_margin", "margin_after_loss", "loss_cost",
            "cost_purchase", "revenue_returns", "quantity_returned_kg"]


def load_model() -> pd.DataFrame:
    f = pd.read_csv(GOLD / "fact_ventes_jour.csv", dtype={"item_code": str}, parse_dates=["date"])
    dd = pd.read_csv(GOLD / "dim_date.csv", parse_dates=["date"])
    dp = pd.read_csv(GOLD / "dim_produit.csv", dtype={"item_code": str, "category_code": str})
    dc = pd.read_csv(GOLD / "dim_categorie.csv", dtype=str)
    f = (f.merge(dd[["date", "period", "month_in_period", "year_month"]], on="date", validate="m:1")
          .merge(dp[["item_code", "item_label", "category_code", "loss_rate_pct"]], on="item_code", validate="m:1")
          .merge(dc[["category_code", "category_name_fr"]], on="category_code", validate="m:1"))
    return f


def build_payload(f: pd.DataFrame) -> dict:
    """Une seule table 'rows' : produit x mois x période (N / N-1). Assez fine pour filtrer par catégorie,
    produit et mois dans le navigateur, assez légère pour tenir dans un fichier HTML autonome."""
    cats = sorted(f["category_name_fr"].unique())
    cat_idx = {c: i for i, c in enumerate(cats)}
    cur = f[f["period"].isin(["N", "N-1"])].copy()
    cur["ca_promo"] = cur["revenue_net"].where(cur["is_discount"], 0.0)
    cur["mb_promo"] = cur["gross_margin"].where(cur["is_discount"], 0.0)
    cur["mal_promo"] = cur["margin_after_loss"].where(cur["is_discount"], 0.0)
    g = (cur.groupby(["period", "month_in_period", "category_name_fr", "item_label"], as_index=False)
            [["revenue_net", "ca_promo", "mb_promo", "mal_promo", "quantity_sold_kg", "gross_margin", "margin_after_loss", "loss_cost", "cost_purchase"]].sum())
    g["c"] = g["category_name_fr"].map(cat_idx)
    g = g.rename(columns={"period": "p", "month_in_period": "m", "item_label": "item", "revenue_net": "ca",
                          "quantity_sold_kg": "vol", "gross_margin": "mb", "margin_after_loss": "mal",
                          "loss_cost": "lc", "cost_purchase": "cp"}).drop(columns="category_name_fr")
    loss = f.drop_duplicates("item_code").set_index("item_label")["loss_rate_pct"]
    return {
        "categories": cats,
        "months": MONTHS_FR,
        "rows": json.loads(g.round(1).to_json(orient="records")),
        "loss_pct": {k: round(float(v), 2) for k, v in loss.items()},
        "period_labels": {"N": "juil. 2022 – juin 2023", "N-1": "juil. 2021 – juin 2022"},
    }


def main() -> None:
    f = load_model()
    payload = build_payload(f)
    template = (DASH / "template.html").read_text(encoding="utf-8")
    chart_js = (DASH / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    html = (template.replace("/*__CHARTJS__*/", chart_js)
                    .replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False, separators=(",", ":"))))
    out = DASH / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"dashboard écrit : {out} ({out.stat().st_size/1e3:.0f} Ko)")


if __name__ == "__main__":
    main()
