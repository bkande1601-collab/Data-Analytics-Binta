"""Nettoyage de price.csv  (Date, Item Code, Wholesale Price (RMB/kg)).

Rôle : prix de gros (= coût d'achat) par article et par jour. Il existe uniquement les jours où
l'article a été vendu, donc la jointure avec les ventes se fait sur (date, item_code).
"""
from __future__ import annotations

from src.common import (IQR_K_EXTREME, RAW, SILVER, CleaningReport, clean_item_code,
                        iqr_flag_by_group, pd, read_csv, write_csv)


def clean_price(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    rep = CleaningReport("price", rows_in=len(raw))
    df = raw.rename(columns={"Date": "date", "Item Code": "item_code",
                             "Wholesale Price (RMB/kg)": "wholesale_price"}).copy()

    # 1. Types.
    df["item_code"] = clean_item_code(df["item_code"])
    parsed = pd.to_datetime(df["date"].astype("string").str.strip(), format="%Y-%m-%d", errors="coerce")
    rep.add("dates invalides", int(parsed.isna().sum()), "ligne supprimée si non parsable",
            "une date illisible ne peut pas être rattachée à une période de comparaison (N vs N-1)")
    df["date"] = parsed
    df["wholesale_price"] = pd.to_numeric(df["wholesale_price"], errors="coerce")
    df = df.dropna(subset=["date", "item_code"])

    # 2. Manquants / non positifs : un prix de gros <= 0 n'a pas de sens (coût d'achat).
    n_na = int(df["wholesale_price"].isna().sum())
    n_neg = int((df["wholesale_price"] <= 0).sum())
    df = df[df["wholesale_price"] > 0]
    rep.add("prix manquant ou <= 0", n_na + n_neg, "ligne supprimée",
            "un coût d'achat nul ou négatif fausserait la marge ; on préfère ne pas calculer de marge")

    # 3. Doublons (même article, même jour) : on moyenne si les prix diffèrent.
    n_dup = int(df.duplicated(["date", "item_code"]).sum())
    df = df.groupby(["date", "item_code"], as_index=False)["wholesale_price"].mean()
    rep.add("doublons (date, item_code)", n_dup, "moyenne des prix du jour",
            "un seul prix de gros par article et par jour (clé de jointure unique)")

    # 4. Valeurs aberrantes par article (IQR x3) : on garde la valeur brute, on ajoute un flag et un prix
    #    corrigé = médiane des prix 'normaux' du même article (ex. coût d'achat de 0,4 RMB/kg pour un produit vendu 8 RMB/kg).
    df = df.sort_values(["item_code", "date"]).reset_index(drop=True)
    df["is_price_outlier"] = iqr_flag_by_group(df, "wholesale_price", "item_code", IQR_K_EXTREME)
    normal_median = (df[~df["is_price_outlier"]].groupby("item_code")["wholesale_price"].median()
                     .rename("item_median_price"))
    df = df.merge(normal_median, on="item_code", how="left")
    df["wholesale_price_clean"] = df["wholesale_price"].where(~df["is_price_outlier"], df["item_median_price"])
    df = df.drop(columns="item_median_price")
    rep.add(f"prix de gros aberrants (IQR x{IQR_K_EXTREME} par article)", int(df["is_price_outlier"].sum()),
            "flag is_price_outlier + prix corrigé (médiane de l'article)",
            "un coût d'achat aberrant (0,01 ou 141 RMB/kg) ferait exploser ou s'effondrer la marge")

    rep.rows_out = len(df)
    return df, rep


def main() -> None:
    df, rep = clean_price(read_csv(RAW / "price.csv"))
    write_csv(df, SILVER / "price_clean.csv")
    rep.save()
    print(rep.summary())


if __name__ == "__main__":
    main()
