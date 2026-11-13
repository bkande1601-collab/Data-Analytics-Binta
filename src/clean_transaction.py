"""Nettoyage de transaction.csv
(Date, Time, Item Code, Quantity Sold (kilo), Unit Selling Price (RMB/kg), Sale or Return, Discount (Yes/No)).

Rôle : table de FAITS brute : une ligne = une vente (ou un retour) d'un article, à une heure précise.
"""
from __future__ import annotations

from src.common import (IQR_K_EXTREME, RAW, SILVER, CleaningReport, clean_item_code,
                        iqr_flag_by_group, pd, read_csv, write_csv)


def clean_transaction(raw: pd.DataFrame, valid_codes: set[str] | None = None) -> tuple[pd.DataFrame, CleaningReport]:
    rep = CleaningReport("transaction", rows_in=len(raw))
    df = raw.rename(columns={"Date": "date", "Time": "time", "Item Code": "item_code",
                             "Quantity Sold (kilo)": "quantity_kg", "Unit Selling Price (RMB/kg)": "unit_price",
                             "Sale or Return": "sale_or_return", "Discount (Yes/No)": "discount"}).copy()

    # 1. Types simples.
    df["item_code"] = clean_item_code(df["item_code"])
    df["quantity_kg"] = pd.to_numeric(df["quantity_kg"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["sale_or_return"] = df["sale_or_return"].astype("string").str.strip().str.lower()
    rep.add("conversion types numériques / code texte", len(df), "float / string", "calculs de CA et de volume")

    # 2. Dates et heures. 'Time' existe avec 8, 10, 11 ou 12 caractères (millisecondes tronquées quand elles
    #    finissent par 0) -> on complète pour obtenir un format unique HH:MM:SS.mmm.
    n_short = int((df["time"].astype("string").str.len() != 12).sum())
    t = df["time"].astype("string").str.strip()
    parts = t.str.split(".", n=1, expand=True)
    frac = parts[1].fillna("") if parts.shape[1] > 1 else pd.Series("", index=t.index, dtype="string")
    t_fixed = parts[0] + "." + frac.str.ljust(3, "0")
    df["datetime"] = pd.to_datetime(df["date"].astype("string").str.strip() + " " + t_fixed,
                                    format="%Y-%m-%d %H:%M:%S.%f", errors="coerce")
    n_bad_dt = int(df["datetime"].isna().sum())
    df["date"] = df["datetime"].dt.normalize()
    df = df.dropna(subset=["datetime"])
    rep.add("heures à millisecondes tronquées (formats hétérogènes)", n_short,
            "complétées à 3 décimales + colonne datetime", "permet de trier les tickets et d'analyser par heure")
    rep.add("date/heure illisibles", n_bad_dt, "ligne supprimée", "sans date, la vente ne peut pas être comparée à N-1")

    # 3. Remise : Yes/No -> booléen.
    df["is_discount"] = df["discount"].astype("string").str.strip().str.lower().map({"yes": True, "no": False})
    n_disc_na = int(df["is_discount"].isna().sum())
    df["is_discount"] = df["is_discount"].fillna(False).astype(bool)
    df = df.drop(columns="discount")
    rep.add("remise (Yes/No) -> booléen", n_disc_na, "valeurs inconnues = pas de remise",
            "le prix vendu inclut déjà la remise ; on l'utilise pour mesurer l'effet promo")

    # 4. Ventes vs retours : le retour est stocké avec une quantité négative. On vérifie la cohérence
    #    type <-> signe, puis on dérive is_return. On GARDE les retours (CA net = ventes - retours).
    incoh = ((df["sale_or_return"] == "sale") & (df["quantity_kg"] < 0)) | \
            ((df["sale_or_return"] == "return") & (df["quantity_kg"] > 0))
    df.loc[incoh, "sale_or_return"] = df.loc[incoh, "quantity_kg"].lt(0).map({True: "return", False: "sale"})
    rep.add("incohérence type (sale/return) vs signe de la quantité", int(incoh.sum()),
            "type recalculé d'après le signe", "le signe de la quantité fait foi")
    df["is_return"] = df["sale_or_return"].eq("return")
    n_ret = int(df["is_return"].sum())
    rep.add("retours (quantité négative)", n_ret, "conservés, flag is_return ; qté retournée en positif à part",
            "le CA 'net' = ventes - retours ; les ignorer surévaluerait le CA, les supprimer sans les compter aussi")

    # 5. Invalides : quantité nulle ou prix <= 0 ou manquants.
    invalid = df["quantity_kg"].isna() | df["unit_price"].isna() | (df["quantity_kg"] == 0) | (df["unit_price"] <= 0)
    rep.add("quantité nulle/manquante ou prix <= 0", int(invalid.sum()), "ligne supprimée",
            "ne représente aucune vente réelle")
    df = df[~invalid]

    # 6. Doublons stricts (même instant, même article, même quantité/prix/type) : double enregistrement.
    keys = ["datetime", "item_code", "quantity_kg", "unit_price", "sale_or_return", "is_discount"]
    n_dup = int(df.duplicated(keys).sum())
    df = df.drop_duplicates(keys, keep="first")
    rep.add("doublons stricts", n_dup, "1re occurrence conservée",
            "deux lignes identiques à la milliseconde = double scan, pas deux ventes")

    # 7. Intégrité référentielle : article inconnu de product.csv.
    if valid_codes is not None:
        orphans = ~df["item_code"].isin(valid_codes)
        rep.add("item_code absent de product.csv (orphelins)", int(orphans.sum()), "ligne supprimée",
                "sans catégorie la vente ne peut pas apparaître dans l'analyse par catégorie")
        df = df[~orphans]

    # 8. Valeurs aberrantes (IQR x3 par article) sur quantité et prix, pour les ventes uniquement.
    sales = ~df["is_return"]
    df["is_qty_outlier"] = False
    df["is_price_outlier"] = False
    tmp = df.loc[sales, ["item_code", "quantity_kg", "unit_price"]]
    df.loc[sales, "is_qty_outlier"] = iqr_flag_by_group(tmp, "quantity_kg", "item_code", IQR_K_EXTREME)
    df.loc[sales, "is_price_outlier"] = iqr_flag_by_group(tmp, "unit_price", "item_code", IQR_K_EXTREME)
    rep.add(f"quantités aberrantes (IQR x{IQR_K_EXTREME} par article, ex. 160 kg en une ligne)",
            int(df["is_qty_outlier"].sum()), "flag is_qty_outlier (conservées)",
            "achats en gros possibles (restauration) : on signale, et on mesure leur poids dans le CA")
    rep.add(f"prix de vente aberrants (IQR x{IQR_K_EXTREME} par article)", int(df["is_price_outlier"].sum()),
            "flag is_price_outlier (conservées)",
            "le prix peut réellement varier fortement (saison, remise) : on signale sans supprimer")

    # 9. Mesures dérivées. Quantités/CA signés : un retour compte négativement dans le net.
    df["revenue"] = (df["quantity_kg"] * df["unit_price"]).round(4)           # CA signé (net des retours)
    df["quantity_sold_kg"] = df["quantity_kg"].where(~df["is_return"], 0.0)  # volume vendu hors retours
    df["quantity_returned_kg"] = (-df["quantity_kg"]).where(df["is_return"], 0.0)

    df = df.sort_values("datetime").reset_index(drop=True)
    cols = ["datetime", "date", "item_code", "quantity_kg", "unit_price", "sale_or_return", "is_return",
            "is_discount", "revenue", "quantity_sold_kg", "quantity_returned_kg", "is_qty_outlier", "is_price_outlier"]
    df = df[cols]
    rep.rows_out = len(df)
    return df, rep


def main() -> None:
    product_path = SILVER / "product_clean.csv"
    valid = set(pd.read_csv(product_path, dtype=str)["item_code"]) if product_path.exists() else None
    df, rep = clean_transaction(read_csv(RAW / "transaction.csv"), valid)
    write_csv(df, SILVER / "transaction_clean.csv")
    rep.save()
    print(rep.summary())


if __name__ == "__main__":
    main()
