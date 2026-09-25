"""Partite della Nazionale italiana di calcio (maschile) dal dataset aperto di Mart Jürisoo.

https://github.com/martj42/international_results: risultati delle nazionali dal 1872, licenza CC0.
Teniamo solo le partite dell'Italia.
"""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pandas as pd

URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
COLUMNS = ["date", "opponent", "goals_for", "goals_against", "tournament", "home"]
TEAM = "Italy"


def fetch_italy(since: str = "1997-01-01") -> pd.DataFrame:
    r = httpx.get(URL, timeout=60, follow_redirects=True)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df = df[(df["date"] >= since) & ((df["home_team"] == TEAM) | (df["away_team"] == TEAM))]
    df = df.dropna(subset=["home_score", "away_score"])  # partite future o senza risultato
    home = df["home_team"] == TEAM
    return pd.DataFrame(
        {
            "date": df["date"],
            "opponent": df["away_team"].where(home, df["home_team"]),
            "goals_for": df["home_score"].where(home, df["away_score"]).astype(int),
            "goals_against": df["away_score"].where(home, df["home_score"]).astype(int),
            "tournament": df["tournament"],
            "home": home & ~df["neutral"].astype(bool),
        }
    ).reset_index(drop=True)


def update_nazionale(path: Path) -> int:
    """Riscarica le partite (il file è piccolo); restituisce quante sono nuove."""
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    new = fetch_italy()
    path.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(path, index=False, lineterminator="\n")
    return len(new) - len(old)


def result(goals_for: int, goals_against: int) -> str:
    if goals_for > goals_against:
        return "vittoria"
    if goals_for < goals_against:
        return "sconfitta"
    return "pareggio"


def match_labels(draw_dates: pd.Series, path: Path) -> pd.Series:
    """Per ogni estrazione: risultato dell'Italia quel giorno, oppure "nessuna partita"."""
    matches = pd.read_csv(path, parse_dates=["date"])
    by_day = {
        row.date: result(row.goals_for, row.goals_against) for row in matches.itertuples(index=False)
    }
    return pd.Series([by_day.get(d, "nessuna partita") for d in draw_dates], name="nazionale")
