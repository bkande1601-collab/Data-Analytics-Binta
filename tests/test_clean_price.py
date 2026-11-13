import pandas as pd

from src.clean_price import clean_price


def test_duplicates_negative_and_outlier_correction():
    n = 40
    dates = pd.date_range("2022-01-01", periods=n).strftime("%Y-%m-%d").tolist()
    prices = ["5.0"] * n
    prices[10] = "500.0"                                   # prix aberrant
    raw = pd.DataFrame({"Date": dates, "Item Code": ["102900005115168"] * n, "Wholesale Price (RMB/kg)": prices})
    raw = pd.concat([raw, pd.DataFrame({"Date": ["2022-01-01"], "Item Code": ["102900005115168"],
                                        "Wholesale Price (RMB/kg)": ["5.0"]}),                   # doublon
                     pd.DataFrame({"Date": ["2022-03-01"], "Item Code": ["102900005115168"],
                                   "Wholesale Price (RMB/kg)": ["-1"]})], ignore_index=True)    # négatif
    df, _ = clean_price(raw)
    assert len(df) == n
    assert df["is_price_outlier"].sum() == 1
    assert df.loc[df["is_price_outlier"], "wholesale_price_clean"].iloc[0] == 5.0
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
