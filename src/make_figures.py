"""Génère les images du README (schémas de modélisation, contrôles qualité, graphiques clés).
Usage : python -m src.make_figures   (nécessite data/gold et docs/reports ; le gros fichier brut n'est pas requis)."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from src.build_dashboard import load_model
from src.common import GOLD, REPORTS, ROOT, SILVER, pd

FIG = ROOT / "figures"
BLUE, GREY, RED, GREEN, AMBER = "#1f6feb", "#b6bdc9", "#d92d20", "#12926b", "#e8a317"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "figure.dpi": 130})


def box(ax, x, y, w, title, fields, color, h_line=0.34):
    h = 0.5 + h_line * (len(fields) + 0.6)
    ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0.02", fc="white", ec=color, lw=2))
    ax.add_patch(FancyBboxPatch((x, y - 0.5), w, 0.5, boxstyle="round,pad=0.02", fc=color, ec=color))
    ax.text(x + w / 2, y - 0.25, title, ha="center", va="center", color="white", fontweight="bold")
    for i, f in enumerate(fields):
        ax.text(x + 0.1, y - 0.5 - h_line * (i + 0.9), f, va="center", fontsize=8.5,
                fontweight="bold" if ("PK" in f or "FK" in f) else "normal")
    return {"x": x, "y": y, "w": w, "h": h}


def link(ax, a, b, label="", sa="r", sb="l", ya=0.0, yb=0.0):
    def pt(bx, side, dy):
        return {"r": (bx["x"] + bx["w"], bx["y"] - 0.25 + dy), "l": (bx["x"], bx["y"] - 0.25 + dy),
                "b": (bx["x"] + bx["w"] / 2, bx["y"] - bx["h"]), "t": (bx["x"] + bx["w"] / 2, bx["y"])}[side]
    (x1, y1), (x2, y2) = pt(a, sa, ya), pt(b, sb, yb)
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", color="#475467", lw=1.4))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", fontsize=8, color="#475467")


def fig_er() -> None:
    fig, ax = plt.subplots(figsize=(11, 6)); ax.set_xlim(0, 13.2); ax.set_ylim(-6.2, 1.8); ax.axis("off")
    t = box(ax, 0.2, 0, 3.7, "transaction.csv (brut)", ["Date", "Time", "Item Code (FK)", "Quantity Sold (kilo)",
            "Unit Selling Price (RMB/kg)", "Sale or Return", "Discount (Yes/No)"], BLUE)
    pr = box(ax, 5.2, 0, 3.0, "product.csv (brut)", ["Item Code (PK)", "Item Name", "Category Code", "Category Name"], AMBER)
    p = box(ax, 9.5, 0, 3.5, "price.csv (brut)", ["Date (PK)", "Item Code (PK, FK)", "Wholesale Price (RMB/kg)"], GREEN)
    lr = box(ax, 5.2, -3.4, 3.0, "loss_rate.csv (brut)", ["Item Code (PK, FK)", "Item Name", "Loss Rate (%)"], RED)
    link(ax, t, pr, "Item Code", "r", "l", -0.55, -0.0)
    link(ax, p, pr, "Item Code", "l", "r", -0.55, -0.0)
    link(ax, lr, pr, "Item Code (1-1)", "t", "b")
    ax.annotate("", (11.2, 0.05), (2.0, 0.05), arrowprops=dict(arrowstyle="-|>", color="#475467", lw=1.4, connectionstyle="arc3,rad=-0.3", linestyle="--"))
    ax.text(6.7, 1.45, "Date + Item Code (prix de gros du jour)", fontsize=8, color="#475467", ha="center")
    ax.text(0.2, -5.6, "Cardinalités : 1 produit → N transactions · 1 produit → N prix (1 par jour de vente) · 1 produit → 1 taux de perte.\n"
            "Clé de jointure : Item Code (texte de 15 chiffres) ; clé composite (Date, Item Code) pour joindre le prix de gros aux ventes.", fontsize=9)
    ax.set_title("Modèle relationnel des 4 fichiers bruts", loc="left")
    fig.savefig(FIG / "modele_relationnel.png", bbox_inches="tight"); plt.close(fig)


def fig_star() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2)); ax.set_xlim(0, 13); ax.set_ylim(-6.4, 0.6); ax.axis("off")
    fact = box(ax, 4.6, -1.0, 4.0, "FAIT : fact_ventes", ["date (FK) → dim_date", "item_code (FK) → dim_produit",
              "is_discount, is_return", "quantity_kg, quantity_sold_kg", "unit_price, revenue", "wholesale_price_clean",
              "cost_purchase, cost_with_loss", "gross_margin, margin_after_loss", "loss_cost"], BLUE)
    d = box(ax, 0.2, 0, 3.4, "DIM : dim_date", ["date (PK)", "year, month, quarter", "year_month, iso_week", "weekday, is_weekend",
            "period (N / N-1 / N-2)", "month_in_period"], GREEN)
    pr = box(ax, 9.4, 0, 3.4, "DIM : dim_produit", ["item_code (PK)", "item_name, item_label", "category_code (FK)",
             "loss_rate_pct, loss_rate", "is_loss_outlier, is_zero_loss"], AMBER)
    c = box(ax, 9.4, -3.6, 3.4, "DIM : dim_categorie", ["category_code (PK)", "category_name", "category_name_fr"], RED)
    link(ax, fact, d, "", "l", "r", -0.0, -0.9); link(ax, fact, pr, "", "r", "l", -0.0, -0.9); link(ax, pr, c, "", "b", "t")
    ax.text(0.2, -5.5, "Grain de la table de faits : 1 ligne = 1 ticket (vente ou retour). Une version agrégée (date × produit × remise),\n"
            "fact_ventes_jour.csv, alimente le dashboard sans le fichier de 880 000 lignes.", fontsize=9)
    ax.set_title("Modèle en étoile (couche Gold)", loc="left")
    fig.savefig(FIG / "modele_etoile.png", bbox_inches="tight"); plt.close(fig)


def fig_cleaning() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, table in zip(axes.ravel(), ["transaction", "product", "price", "loss_rate"]):
        rep = json.loads((REPORTS / f"cleaning_{table}.json").read_text(encoding="utf-8"))
        rules = [r for r in rep["regles"] if r["lignes_concernees"] > 0 and not r["regle"].startswith(("conversion", "codes en texte", "BOM", "traduction"))]
        rules = sorted(rules, key=lambda r: r["lignes_concernees"])
        labels = [(r["regle"][:48] + "…") if len(r["regle"]) > 48 else r["regle"] for r in rules]
        ax.barh(labels, [r["lignes_concernees"] for r in rules], color=BLUE)
        for i, r in enumerate(rules):
            ax.text(r["lignes_concernees"], i, f" {r['lignes_concernees']:,}".replace(",", " "), va="center", fontsize=8)
        ax.set_title(f"{table} : {rep['lignes_entree']:,} → {rep['lignes_sortie']:,} lignes".replace(",", " "), fontsize=10)
        ax.tick_params(axis="y", labelsize=7.5); ax.margins(x=0.25)
    fig.suptitle("Lignes touchées par chaque règle de nettoyage (les lignes sont corrigées ou signalées, rarement supprimées)", fontweight="bold")
    fig.tight_layout(); fig.savefig(FIG / "nettoyage_regles.png", bbox_inches="tight"); plt.close(fig)


def fig_quality() -> None:
    raw_tx = pd.read_csv(SILVER / "transaction_clean.csv", usecols=["date", "item_code", "unit_price", "quantity_kg", "is_return"],
                         dtype={"item_code": str})
    price = pd.read_csv(SILVER / "price_clean.csv", dtype={"item_code": str}, parse_dates=["date"])
    loss = pd.read_csv(SILVER / "loss_rate_clean.csv")
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    ax[0].hist(raw_tx.loc[~raw_tx["is_return"], "quantity_kg"].clip(upper=5), bins=60, color=BLUE)
    ax[0].set_title("Quantité par ligne de vente (kg, ≤ 5)", fontsize=10); ax[0].set_xlabel("kg"); ax[0].set_ylabel("lignes")
    big = price["item_code"].value_counts(); big = big[big >= 300].index
    item = price[price["item_code"].isin(big) & price["is_price_outlier"]].groupby("item_code").size().idxmax()
    s = price[price["item_code"] == item]
    ax[1].plot(s["date"], s["wholesale_price"], lw=0.8, color=GREY, label="prix brut")
    ax[1].scatter(s.loc[s["is_price_outlier"], "date"], s.loc[s["is_price_outlier"], "wholesale_price"], color=RED, s=14, label="aberrant (IQR×3)", zorder=3)
    ax[1].plot(s["date"], s["wholesale_price_clean"], lw=1.1, color=BLUE, label="prix corrigé")
    ax[1].set_title("Prix de gros d'un article : aberrations", fontsize=10); ax[1].tick_params(axis="x", rotation=30); ax[1].legend(fontsize=8)
    ax[2].hist(loss["loss_rate_pct"], bins=30, color=AMBER)
    ax[2].scatter(loss.loc[loss["is_loss_outlier"], "loss_rate_pct"], [2] * int(loss["is_loss_outlier"].sum()), color=RED, zorder=3, label="aberrant (IQR×3)")
    ax[2].set_title("Taux de perte par article (%) : pic à 9,43 %", fontsize=10); ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "controles_qualite.png", bbox_inches="tight"); plt.close(fig)


def fig_insights() -> None:
    f = load_model()
    cur = f[f["period"].isin(["N", "N-1"])]
    g = cur.groupby(["category_name_fr", "period"])[["revenue_net", "gross_margin", "margin_after_loss", "loss_cost", "cost_purchase"]].sum().unstack()
    evo = (g[("revenue_net", "N")] / g[("revenue_net", "N-1")] - 1).sort_values()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.barh(evo.index, evo * 100, color=[RED if v < 0 else BLUE for v in evo])
    for i, v in enumerate(evo): ax.text(v * 100 + (1 if v > 0 else -1), i, f"{v*100:+.0f} %", va="center", ha="left" if v > 0 else "right", fontsize=9)
    ax.set_title("Évolution du CA net N vs N-1, par catégorie"); ax.set_xlabel("%"); ax.margins(x=0.15)
    fig.tight_layout(); fig.savefig(FIG / "dataviz_evolution_ca.png", bbox_inches="tight"); plt.close(fig)

    mal = pd.DataFrame({"N-1": g[("margin_after_loss", "N-1")] / g[("revenue_net", "N-1")], "N": g[("margin_after_loss", "N")] / g[("revenue_net", "N")]}).sort_values("N")
    fig, ax = plt.subplots(figsize=(8, 3.8)); y = range(len(mal))
    ax.barh([i + 0.2 for i in y], mal["N-1"] * 100, 0.4, color=GREY, label="N-1")
    ax.barh([i - 0.2 for i in y], mal["N"] * 100, 0.4, color=BLUE, label="N")
    ax.set_yticks(list(y)); ax.set_yticklabels(mal.index); ax.set_title("Marge après pertes (% du CA)"); ax.legend(); ax.set_xlabel("%")
    fig.tight_layout(); fig.savefig(FIG / "dataviz_marge_apres_pertes.png", bbox_inches="tight"); plt.close(fig)

    d = cur[cur["period"] == "N"].groupby("is_discount")[["revenue_net", "gross_margin", "margin_after_loss"]].sum()
    fig, ax = plt.subplots(figsize=(6, 3.8)); x = [0, 1]
    ax.bar([i - 0.2 for i in x], d["gross_margin"] / d["revenue_net"] * 100, 0.4, color=BLUE, label="Marge brute")
    ax.bar([i + 0.2 for i in x], d["margin_after_loss"] / d["revenue_net"] * 100, 0.4, color=AMBER, label="Marge après pertes")
    for i, (a, b) in enumerate(zip(d["gross_margin"] / d["revenue_net"], d["margin_after_loss"] / d["revenue_net"])):
        ax.text(i - 0.2, a * 100 + 1, f"{a*100:.0f} %", ha="center"); ax.text(i + 0.2, b * 100 + 1, f"{b*100:.0f} %", ha="center")
    ax.set_xticks(x); ax.set_xticklabels(["Sans remise", "Avec remise"]); ax.legend(); ax.set_title("Effet des remises sur la marge (N)")
    fig.tight_layout(); fig.savefig(FIG / "dataviz_remises.png", bbox_inches="tight"); plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    for fn in (fig_er, fig_star, fig_cleaning, fig_quality, fig_insights):
        fn(); print("ok", fn.__name__)


if __name__ == "__main__":
    main()
