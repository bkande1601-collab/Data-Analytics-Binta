"""Nettoyage de loss_rate.csv  (Item Code, Item Name, Loss Rate (%)).

Rôle : taux de perte (casse, péremption, déchets) par article, en % des quantités achetées.
"""
from __future__ import annotations

from src.common import (IQR_K_EXTREME, RAW, SILVER, CleaningReport, clean_item_code, clean_text,
                        iqr_bounds, pd, read_csv, write_csv)


def clean_loss_rate(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    rep = CleaningReport("loss_rate", rows_in=len(raw))
    df = raw.rename(columns={"Item Code": "item_code", "Item Name": "item_name",
                             "Loss Rate (%)": "loss_rate_pct"}).copy()

    # 1. Types.
    df["item_code"] = clean_item_code(df["item_code"])
    rep.add("BOM + code en texte", len(df), "encodage utf-8-sig, code en string",
            "le fichier commence par un caractère invisible (BOM) qui renommerait la 1re colonne")

    # 2. Espaces parasites : la valeur numérique est écrite '4.39 ' (espace final) et certains noms aussi.
    n_name = int((df["item_name"].astype("string") != clean_text(df["item_name"])).sum())
    df["item_name"] = clean_text(df["item_name"])
    rep.add("espaces parasites (item_name)", n_name, "strip", "cohérence avec product.csv")
    raw_rate = df["loss_rate_pct"].astype("string")
    n_rate = int((raw_rate != raw_rate.str.strip()).sum())
    df["loss_rate_pct"] = pd.to_numeric(raw_rate.str.strip().str.replace(",", ".", regex=False), errors="coerce")
    rep.add("espace final dans le taux + conversion numérique", n_rate, "strip puis float",
            "sans cela le taux reste du texte et aucune moyenne n'est possible")

    # 3. Manquants / hors bornes : un taux de perte est un pourcentage compris entre 0 et 100.
    n_na = int(df["loss_rate_pct"].isna().sum())
    rep.add("taux manquant ou illisible", n_na,
            "laissé NaN ici ; imputé par la médiane de la catégorie à la consolidation (flag)",
            "la médiane de catégorie est robuste aux valeurs extrêmes (consigne cours : médiane)")
    bad = int(((df["loss_rate_pct"] < 0) | (df["loss_rate_pct"] > 100)).sum())
    df = df[~((df["loss_rate_pct"] < 0) | (df["loss_rate_pct"] > 100))]
    rep.add("taux hors [0 ; 100] %", bad, "ligne supprimée", "un pourcentage de perte ne peut pas sortir de cet intervalle")

    # 4. Doublons.
    n_dup = int(df.duplicated("item_code").sum())
    df = df.drop_duplicates("item_code", keep="first")
    rep.add("doublons sur item_code", n_dup, "1re occurrence conservée", "un seul taux de perte par article")

    # 5. Valeurs aberrantes (IQR x3) : signalées, pas supprimées (une perte de 29 % sur un champignon
    #    frais est plausible ; c'est justement le signal que cherche le Comex).
    lo, hi = iqr_bounds(df["loss_rate_pct"].dropna(), IQR_K_EXTREME)
    df["is_loss_outlier"] = (df["loss_rate_pct"] < lo) | (df["loss_rate_pct"] > hi)
    rep.add(f"valeurs aberrantes IQR x{IQR_K_EXTREME} (bornes {lo:.1f} - {hi:.1f} %)", int(df["is_loss_outlier"].sum()),
            "colonne is_loss_outlier (lignes conservées)",
            "une perte très élevée est une information métier, pas une erreur de saisie")
    n_zero = int((df["loss_rate_pct"] == 0).sum())
    df["is_zero_loss"] = df["loss_rate_pct"] == 0
    rep.add("taux = 0 %", n_zero, "colonne is_zero_loss (conservé)",
            "0 % de perte sur un produit frais est suspect : à signaler au métier, pas à corriger seul")

    df["loss_rate"] = df["loss_rate_pct"] / 100  # fraction, pratique pour les calculs de coût
    df = df.sort_values("item_code").reset_index(drop=True)
    rep.rows_out = len(df)
    return df, rep


def main() -> None:
    df, rep = clean_loss_rate(read_csv(RAW / "loss_rate.csv"))
    write_csv(df, SILVER / "loss_rate_clean.csv")
    rep.save()
    print(rep.summary())


if __name__ == "__main__":
    main()
