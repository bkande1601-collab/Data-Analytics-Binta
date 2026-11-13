"""Utilitaires communs aux 4 scripts de nettoyage : chemins, lecture, rapport de nettoyage."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SILVER = ROOT / "data" / "silver"
GOLD = ROOT / "data" / "gold"
REPORTS = ROOT / "docs" / "reports"

# Règle IQR vue en cours (slide 24) : Q1 - k*IQR / Q3 + k*IQR.
IQR_K_OUTLIER = 1.5   # valeur aberrante "classique"
IQR_K_EXTREME = 3.0   # valeur extrême (celle que l'on signale dans nos flags)


@dataclass
class CleaningReport:
    """Garde la trace de chaque règle appliquée et du nombre de lignes concernées."""

    table: str
    rows_in: int = 0
    rows_out: int = 0
    rules: list[dict] = field(default_factory=list)

    def add(self, rule: str, affected: int, action: str, why: str) -> None:
        self.rules.append({"regle": rule, "lignes_concernees": int(affected),
                           "action": action, "justification_metier": why})

    def to_dict(self) -> dict:
        return {"table": self.table, "lignes_entree": self.rows_in,
                "lignes_sortie": self.rows_out, "regles": self.rules}

    def save(self, directory: Path = REPORTS) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"cleaning_{self.table}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def summary(self) -> str:
        lines = [f"[{self.table}] {self.rows_in:,} -> {self.rows_out:,} lignes"]
        lines += [f"  - {r['regle']}: {r['lignes_concernees']:,} ({r['action']})" for r in self.rules]
        return "\n".join(lines)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    """Lecture 'tout en texte' : on convertit nous-mêmes les types (pas d'inférence silencieuse).
    utf-8-sig retire l'éventuel BOM présent en tête de fichier (cas de loss_rate.csv)."""
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False,
                       na_values=["", "NA", "N/A", "null", "NULL", "nan"], **kwargs)


def clean_text(s: pd.Series) -> pd.Series:
    """Supprime les espaces en début/fin et réduit les espaces multiples."""
    return s.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)


def clean_item_code(s: pd.Series) -> pd.Series:
    """Clé de jointure : texte, sans espaces ni '.0' (pour ne pas perdre de chiffres en float)."""
    return s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def iqr_bounds(s: pd.Series, k: float) -> tuple[float, float]:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def iqr_flag_by_group(df: pd.DataFrame, value: str, group: str, k: float, min_obs: int = 30) -> pd.Series:
    """True si la valeur sort des bornes IQR calculées *par produit* (un produit à 120 RMB/kg n'est
    pas anormal en soi, c'est un écart par rapport à son propre historique qui l'est).
    Les produits avec moins de `min_obs` observations ne sont pas évalués (quartiles non fiables)."""
    g = df.groupby(group)[value]
    q1, q3 = g.transform(lambda x: x.quantile(0.25)), g.transform(lambda x: x.quantile(0.75))
    iqr = q3 - q1
    enough = g.transform("count") >= min_obs
    return enough & ((df[value] < q1 - k * iqr) | (df[value] > q3 + k * iqr))


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


__all__ = ["ROOT", "RAW", "SILVER", "GOLD", "REPORTS", "CleaningReport", "read_csv", "clean_text",
           "clean_item_code", "iqr_bounds", "iqr_flag_by_group", "write_csv", "np", "pd",
           "IQR_K_OUTLIER", "IQR_K_EXTREME"]
