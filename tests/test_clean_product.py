import pandas as pd

from src.clean_product import clean_product


def _raw(rows):
    return pd.DataFrame(rows, columns=["Item Code", "Item Name", "Category Code", "Category Name"])


def test_strip_dedupe_and_unique_label():
    raw = _raw([["102900005115168", " Niushou  Shengcai ", "1011010101", "Flower/Leaf Vegetables"],
                ["102900005115168", "Niushou Shengcai", "1011010101", "Flower/Leaf Vegetables"],  # doublon de code
                ["102900005115199", "Chinese Cabbage", "1011010201", "Cabbage"],
                ["102900005115200", "Chinese Cabbage", "1011010201", "Cabbage"]])           # même nom, autre code
    df, rep = clean_product(raw)
    assert len(df) == 3
    assert df.loc[0, "item_name"] == "Niushou Shengcai"
    assert df["item_label"].is_unique
    assert df["item_code"].str.len().eq(15).all()
    assert (df["category_name_fr"] == "Choux").sum() == 2
    assert rep.rows_in == 4 and rep.rows_out == 3
