"""Consolidation : tables SILVER (propres) -> modèle en étoile GOLD.

Schéma en étoile
    dim_date ─┐
    dim_produit ─┼─ fact_ventes (grain : 1 ligne de ticket)   +   fact_ventes_jour (agrégé date x produit x remise)
    dim_categorie ┘

Mesures dérivées (définies dans docs/exercice-1 dictionnaire des données) :
    CA net            = quantité x prix de vente (les retours comptent en négatif)
    Coût d'achat      = quantité nette x prix de gros du jour
    Coût avec pertes  = coût d'achat / (1 - taux de perte)   -> on achète plus que ce que l'on vend
    Marge brute       = CA net - coût d'achat
    Marge après pertes= CA net - coût avec pertes
"""
from __future__ import annotations

from src.common import GOLD, SILVER, pd, write_csv

# Découpage en périodes glissantes de 12 mois, alignées sur la fin des données (30/06/2023) :
# N = les 12 derniers mois, N-1 = les 12 mois précédents (comparaison à périmètre identique).
PERIOD_END = pd.Timestamp("2023-06-30")


def period_label(d: pd.Series, end: pd.Timestamp = PERIOD_END) -> pd.Series:
    start_n = end - pd.DateOffset(years=1) + pd.Timedelta(days=1)
    start_n1 = end - pd.DateOffset(years=2) + pd.Timedelta(days=1)
    start_n2 = end - pd.DateOffset(years=3) + pd.Timedelta(days=1)
    out = pd.Series("hors période", index=d.index)
    out[(d >= start_n2) & (d < start_n1)] = "N-2"
    out[(d >= start_n1) & (d < start_n)] = "N-1"
    out[(d >= start_n) & (d <= end)] = "N"
    return out


def build_dim_categorie(product: pd.DataFrame) -> pd.DataFrame:
    cat = (product[["category_code", "category_name", "category_name_fr"]].drop_duplicates()
           .sort_values("category_code").reset_index(drop=True))
    return cat


def build_dim_produit(product: pd.DataFrame, loss: pd.DataFrame) -> pd.DataFrame:
    dim = product.merge(loss[["item_code", "loss_rate_pct", "loss_rate", "is_loss_outlier", "is_zero_loss"]],
                        on="item_code", how="left", validate="1:1")
    # Imputation de la médiane de catégorie pour les taux manquants (aucun cas aujourd'hui, prévu par sécurité).
    dim["loss_rate_imputed"] = dim["loss_rate_pct"].isna()
    med = dim.groupby("category_code")["loss_rate_pct"].transform("median")
    dim["loss_rate_pct"] = dim["loss_rate_pct"].fillna(med).fillna(dim["loss_rate_pct"].median())
    dim["loss_rate"] = dim["loss_rate_pct"] / 100
    dim["is_loss_outlier"] = dim["is_loss_outlier"].fillna(False)
    dim["is_zero_loss"] = dim["is_zero_loss"].fillna(False)
    return dim.drop(columns=["category_name", "category_name_fr"])


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    d = pd.DataFrame({"date": pd.date_range(dates.min(), dates.max(), freq="D")})
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    d["year_month"] = d["date"].dt.strftime("%Y-%m")
    d["quarter"] = d["date"].dt.quarter
    d["iso_week"] = d["date"].dt.isocalendar().week.astype(int)
    d["weekday"] = d["date"].dt.dayofweek + 1  # 1 = lundi
    d["is_weekend"] = d["weekday"] >= 6
    d["period"] = period_label(d["date"])
    # Mois équivalent dans l'année glissante (1 = juillet ... 12 = juin) pour comparer N et N-1 mois par mois.
    d["month_in_period"] = ((d["month"] - 7) % 12) + 1
    return d


def build_fact_ventes(tx: pd.DataFrame, price: pd.DataFrame, dim_prod: pd.DataFrame) -> pd.DataFrame:
    f = tx.merge(price[["date", "item_code", "wholesale_price", "wholesale_price_clean", "is_price_outlier"]]
                 .rename(columns={"is_price_outlier": "is_wholesale_outlier"}),
                 on=["date", "item_code"], how="left", validate="m:1")
    f = f.merge(dim_prod[["item_code", "category_code", "loss_rate"]], on="item_code", how="left", validate="m:1")
    f["has_cost"] = f["wholesale_price_clean"].notna()
    f["cost_purchase"] = f["quantity_kg"] * f["wholesale_price_clean"]
    f["cost_with_loss"] = f["cost_purchase"] / (1 - f["loss_rate"])
    f["gross_margin"] = f["revenue"] - f["cost_purchase"]
    f["margin_after_loss"] = f["revenue"] - f["cost_with_loss"]
    f["loss_cost"] = f["cost_with_loss"] - f["cost_purchase"]  # valeur détruite par les pertes
    return f.drop(columns=["loss_rate"])


def build_fact_jour(f: pd.DataFrame) -> pd.DataFrame:
    g = f.assign(
        revenue_sales=f["revenue"].where(~f["is_return"], 0.0),
        revenue_returns=f["revenue"].where(f["is_return"], 0.0),
        n_lines=1, n_returns=f["is_return"].astype(int),
        revenue_costed=f["revenue"].where(f["has_cost"], 0.0),
    ).groupby(["date", "item_code", "is_discount"], as_index=False).agg(
        n_lines=("n_lines", "sum"), n_returns=("n_returns", "sum"),
        quantity_sold_kg=("quantity_sold_kg", "sum"), quantity_returned_kg=("quantity_returned_kg", "sum"),
        revenue_sales=("revenue_sales", "sum"), revenue_returns=("revenue_returns", "sum"),
        revenue_net=("revenue", "sum"), revenue_costed=("revenue_costed", "sum"),
        cost_purchase=("cost_purchase", "sum"), cost_with_loss=("cost_with_loss", "sum"),
        gross_margin=("gross_margin", "sum"), margin_after_loss=("margin_after_loss", "sum"),
        loss_cost=("loss_cost", "sum"),
    )
    return g.round(4)


def main() -> None:
    product = pd.read_csv(SILVER / "product_clean.csv", dtype={"item_code": str, "category_code": str})
    loss = pd.read_csv(SILVER / "loss_rate_clean.csv", dtype={"item_code": str})
    price = pd.read_csv(SILVER / "price_clean.csv", dtype={"item_code": str}, parse_dates=["date"])
    tx = pd.read_csv(SILVER / "transaction_clean.csv", dtype={"item_code": str}, parse_dates=["datetime", "date"])

    dim_cat = build_dim_categorie(product)
    dim_prod = build_dim_produit(product, loss)
    dim_date = build_dim_date(tx["date"])
    fact = build_fact_ventes(tx, price, dim_prod)
    fact_jour = build_fact_jour(fact)

    assert fact["item_code"].isin(dim_prod["item_code"]).all(), "clé étrangère item_code orpheline"
    assert fact["date"].isin(dim_date["date"]).all(), "clé étrangère date orpheline"
    assert len(fact) == len(tx), "la jointure ne doit ni dupliquer ni perdre de lignes"
    print(f"fact_ventes: {len(fact):,} lignes | sans coût: {(~fact['has_cost']).sum():,}")

    write_csv(dim_cat, GOLD / "dim_categorie.csv")
    write_csv(dim_prod, GOLD / "dim_produit.csv")
    write_csv(dim_date, GOLD / "dim_date.csv")
    write_csv(fact_jour, GOLD / "fact_ventes_jour.csv")
    write_csv(fact, GOLD / "fact_ventes_transaction.csv")  # volumineux : ignoré par git
    print("gold écrit dans", GOLD)


if __name__ == "__main__":
    main()
