import pandas as pd

from src.clean_loss_rate import clean_loss_rate


def test_trailing_space_numeric_and_flags():
    vals = ["9.4 "] * 20 + ["0.0 ", "60.0 ", "150.0 "]
    raw = pd.DataFrame({"Item Code": [f"10290000511{i:04d}" for i in range(len(vals))],
                        "Item Name": [" A "] * len(vals), "Loss Rate (%)": vals})
    df, rep = clean_loss_rate(raw)
    assert df["loss_rate_pct"].dtype.kind == "f"
    assert len(df) == len(vals) - 1                      # 150 % supprimé (hors [0;100])
    assert df["is_zero_loss"].sum() == 1
    assert df.loc[df["loss_rate_pct"] == 60, "is_loss_outlier"].all()   # 60 % signalé, conservé
    assert df["loss_rate"].max() == 0.6
