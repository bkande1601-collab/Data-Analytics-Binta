import pandas as pd

from src.build_gold import build_dim_date, build_fact_jour, build_fact_ventes, period_label


def test_periods_cover_12_months_each():
    d = build_dim_date(pd.Series(pd.to_datetime(["2020-07-01", "2023-06-30"])))
    counts = d["period"].value_counts()
    assert counts["N"] == 365 and counts["N-1"] == 365 and counts["N-2"] == 365
    assert period_label(pd.Series([pd.Timestamp("2022-07-01")])).iloc[0] == "N"
    assert period_label(pd.Series([pd.Timestamp("2022-06-30")])).iloc[0] == "N-1"


def test_margin_after_loss_formula():
    tx = pd.DataFrame({"datetime": pd.to_datetime(["2023-01-01 10:00", "2023-01-01 11:00"]),
                       "date": pd.to_datetime(["2023-01-01"] * 2), "item_code": ["A", "A"],
                       "quantity_kg": [10.0, -1.0], "unit_price": [10.0, 10.0], "sale_or_return": ["sale", "return"],
                       "is_return": [False, True], "is_discount": [False, False], "revenue": [100.0, -10.0],
                       "quantity_sold_kg": [10.0, 0.0], "quantity_returned_kg": [0.0, 1.0]})
    price = pd.DataFrame({"date": pd.to_datetime(["2023-01-01"]), "item_code": ["A"], "wholesale_price": [4.0],
                          "wholesale_price_clean": [4.0], "is_price_outlier": [False]})
    dim = pd.DataFrame({"item_code": ["A"], "category_code": ["C"], "loss_rate": [0.2]})
    f = build_fact_ventes(tx, price, dim)
    j = build_fact_jour(f).iloc[0]
    assert j["revenue_net"] == 90 and j["cost_purchase"] == 4 * 9
    assert round(j["cost_with_loss"], 2) == 45.0          # 36 / (1 - 0.2)
    assert round(j["margin_after_loss"], 2) == 45.0       # 90 - 45
    assert round(j["loss_cost"], 2) == 9.0
