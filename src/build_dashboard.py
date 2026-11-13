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
    cats = sorted(f["category_name_fr"].unique())
    cat_idx = {c: i for i, c in enumerate(cats)}
    cur = f[f["period"].isin(["N", "N-1"])].copy()
    cur["c"] = cur["category_name_fr"].map(cat_idx)
    cur["d"] = cur["is_discount"].astype(int)
    cur["p"] = cur["period"]

    monthly = (cur.groupby(["p", "month_in_period", "c", "d"], as_index=False)[MEASURES].sum()
               .rename(columns={"month_in_period": "m"}))
    products = (cur.groupby(["p", "c", "d", "item_label"], as_index=False)[MEASURES].sum())
    loss_by_item = f.drop_duplicates("item_code").set_index("item_label")["loss_rate_pct"].to_dict()
    products["loss_pct"] = products["item_label"].map(loss_by_item)

    def rows(df: pd.DataFrame) -> list[dict]:
        return json.loads(df.round(2).to_json(orient="records"))

    return {
        "categories": cats,
        "months": MONTHS_FR,
        "monthly": rows(monthly),
        "products": rows(products),
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
