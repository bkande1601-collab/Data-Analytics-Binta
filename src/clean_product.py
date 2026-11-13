"""Nettoyage de product.csv  (Item Code, Item Name, Category Code, Category Name).

Rôle : dimension PRODUIT. Chaque article (Item Code) appartient à une catégorie de produit frais.
"""
from __future__ import annotations

from src.common import (RAW, SILVER, CleaningReport, clean_item_code, clean_text, pd, read_csv,
                        write_csv)

# Traduction des catégories pour le dashboard en français (le fichier source est en anglais).
CATEGORY_FR = {
    "Flower/Leaf Vegetables": "Légumes feuilles / fleurs",
    "Edible Mushroom": "Champignons comestibles",
    "Capsicum": "Piments & poivrons",
    "Aquatic Tuberous Vegetables": "Légumes aquatiques & tubercules",
    "Solanum": "Solanacées (aubergine, tomate…)",
    "Cabbage": "Choux",
}


def clean_product(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    rep = CleaningReport("product", rows_in=len(raw))
    df = raw.rename(columns={"Item Code": "item_code", "Item Name": "item_name",
                             "Category Code": "category_code", "Category Name": "category_name"}).copy()

    # 1. Types : les codes sont des identifiants (15 chiffres), jamais des nombres -> texte.
    for c in ("item_code", "category_code"):
        df[c] = clean_item_code(df[c])
    rep.add("codes en texte", len(df), "conversion en string",
            "un code de 15 chiffres converti en float perdrait des chiffres et casserait les jointures")

    # 2. Espaces parasites dans les libellés.
    for c in ("item_name", "category_name"):
        before = df[c].copy()
        df[c] = clean_text(df[c])
        n = int((before.astype("string") != df[c]).sum())
        if c == "item_name":
            rep.add("espaces parasites (item_name)", n, "strip + espaces multiples réduits",
                    "évite qu'un même produit apparaisse sous deux écritures dans un filtre du dashboard")

    # 3. Valeurs manquantes sur les clés : une ligne sans clé est inutilisable.
    n_na = int(df[["item_code", "item_name", "category_code", "category_name"]].isna().any(axis=1).sum())
    df = df.dropna(subset=["item_code", "category_code"])
    rep.add("clé ou catégorie manquante", n_na, "ligne supprimée",
            "impossible de rattacher le produit à une transaction ou à une catégorie")

    # 4. Doublons : un même Item Code ne doit apparaître qu'une fois (clé primaire de la dimension).
    n_dup = int(df.duplicated("item_code").sum())
    df = df.drop_duplicates("item_code", keep="first")
    rep.add("doublons sur item_code", n_dup, "on garde la 1re occurrence",
            "clé primaire de la dimension : un doublon multiplierait les ventes lors du JOIN")

    # 5. Cohérence code catégorie <-> libellé catégorie (1 code = 1 libellé).
    incoh = int((df.groupby("category_code")["category_name"].transform("nunique") > 1).sum())
    rep.add("code catégorie avec plusieurs libellés", incoh, "contrôle (aucune action si 0)",
            "garantit une hiérarchie propre pour les graphiques par catégorie")

    # 6. Noms de produits identiques pour des codes différents (ex. 'Chinese Cabbage' x2) : on garde
    #    les deux produits (codes distincts = articles distincts) mais on crée un libellé unique.
    dup_name = df["item_name"].duplicated(keep=False)
    df["item_label"] = df["item_name"].where(~dup_name, df["item_name"] + " [" + df["item_code"].str[-5:] + "]")
    rep.add("noms de produit en double (codes différents)", int(dup_name.sum()), "item_label unique créé",
            "deux articles distincts ne doivent pas être fusionnés mais doivent rester lisibles")

    # 7. Libellé de catégorie en français.
    df["category_name_fr"] = df["category_name"].map(CATEGORY_FR).fillna(df["category_name"])
    rep.add("traduction des catégories", len(df), "colonne category_name_fr ajoutée",
            "dashboard destiné au Comex francophone")

    df = df.sort_values("item_code").reset_index(drop=True)
    rep.rows_out = len(df)
    return df, rep


def main() -> None:
    df, rep = clean_product(read_csv(RAW / "product.csv"))
    write_csv(df, SILVER / "product_clean.csv")
    rep.save()
    print(rep.summary())


if __name__ == "__main__":
    main()
