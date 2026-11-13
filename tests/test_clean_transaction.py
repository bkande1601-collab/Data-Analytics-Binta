import pandas as pd

from src.clean_transaction import clean_transaction

COLS = ["Date", "Time", "Item Code", "Quantity Sold (kilo)", "Unit Selling Price (RMB/kg)", "Sale or Return", "Discount (Yes/No)"]


def test_time_padding_returns_duplicates_orphans():
    raw = pd.DataFrame([
        ["2020-07-01", "09:15:07.924", "102900005115168", "0.5", "7.6", "sale", "No"],
        ["2020-07-01", "09:15:07.924", "102900005115168", "0.5", "7.6", "sale", "No"],      # doublon strict
        ["2020-07-01", "10:00:00.5", "102900005115168", "1.0", "4.0", "sale", "Yes"],       # ms tronquées
        ["2020-07-01", "11:00:00", "102900005115168", "-0.4", "7.6", "return", "No"],       # retour
        ["2020-07-01", "12:00:00", "999999999999999", "1.0", "5.0", "sale", "No"],          # orphelin
        ["2020-07-01", "13:00:00", "102900005115168", "0", "5.0", "sale", "No"],            # quantité nulle
    ], columns=COLS)
    df, rep = clean_transaction(raw, valid_codes={"102900005115168"})
    assert len(df) == 3
    assert set(df["is_return"]) == {True, False}
    ret = df[df["is_return"]].iloc[0]
    assert ret["revenue"] < 0 and ret["quantity_returned_kg"] == 0.4 and ret["quantity_sold_kg"] == 0
    assert df["is_discount"].sum() == 1
    assert df["datetime"].is_monotonic_increasing
