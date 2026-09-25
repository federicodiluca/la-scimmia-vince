"""Statistiche descrittive: quello che trovi anche sui siti dei giocatori, ma fatto per bene."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from scimmia.models import MAX_NUMBER, NUMBERS_PER_DRAW

NUMBER_COLUMNS = [f"n{i}" for i in range(1, NUMBERS_PER_DRAW + 1)]
ALL_NUMBERS = pd.RangeIndex(1, MAX_NUMBER + 1, name="number")
WEEKDAYS_IT = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def hit_matrix(draws: pd.DataFrame) -> np.ndarray:
    """Matrice booleana (estrazioni × 90): True se il numero è nella sestina."""
    hits = np.zeros((len(draws), MAX_NUMBER), dtype=bool)
    rows = np.repeat(np.arange(len(draws)), NUMBERS_PER_DRAW)
    hits[rows, draws[NUMBER_COLUMNS].to_numpy().ravel() - 1] = True
    return hits


def long_numbers(draws: pd.DataFrame) -> pd.DataFrame:
    """Una riga per numero estratto: id, date, number."""
    return (
        draws.melt(id_vars=["id", "date"], value_vars=NUMBER_COLUMNS, value_name="number")
        .drop(columns="variable")
        .sort_values(["date", "number"], ignore_index=True)
    )


def frequency(draws: pd.DataFrame, column: str | None = None) -> pd.Series:
    """Quante volte è uscito ogni numero (1..90). `column` = "jolly" o "superstar"."""
    values = long_numbers(draws)["number"] if column is None else draws[column].dropna().astype(int)
    return values.value_counts().reindex(ALL_NUMBERS, fill_value=0).rename("count")


def group_key(draws: pd.DataFrame, by: str) -> pd.Series:
    dates = draws["date"].dt
    match by:
        case "year":
            return dates.year.rename("year")
        case "month":
            return dates.month.rename("month")
        case "weekday":
            return dates.weekday.map(lambda i: WEEKDAYS_IT[i]).rename("weekday")
        case "isoweek":
            return dates.isocalendar().week.astype(int).rename("isoweek")
        case _:
            raise ValueError(f"raggruppamento sconosciuto: {by}")


def frequency_by(draws: pd.DataFrame, by: str) -> pd.DataFrame:
    """Tabella numero × gruppo (anno, mese, giorno della settimana, settimana ISO)."""
    groups = pd.DataFrame({"id": draws["id"], by: group_key(draws, by)})
    long = long_numbers(draws).merge(groups, on="id")
    return pd.crosstab(long["number"], long[by]).reindex(ALL_NUMBERS, fill_value=0)


def delays(draws: pd.DataFrame) -> pd.DataFrame:
    """Ritardi per numero, misurati in estrazioni.

    - current: estrazioni trascorse dall'ultima uscita
    - max: ritardo più lungo mai registrato (incluso quello in corso)
    - mean: ritardo medio tra due uscite consecutive
    """
    hits = hit_matrix(draws)
    n_draws = len(draws)
    rows = []
    for number in ALL_NUMBERS:
        seen = np.flatnonzero(hits[:, number - 1])
        if len(seen) == 0:
            rows.append((number, n_draws, n_draws, np.nan, None))
            continue
        gaps = np.diff(np.concatenate(([-1], seen))) - 1
        current = n_draws - 1 - seen[-1]
        rows.append(
            (number, int(current), int(max(gaps.max(), current)), float(gaps[1:].mean()) if len(gaps) > 1 else np.nan,
             draws["date"].iloc[seen[-1]].date().isoformat())
        )
    return pd.DataFrame(rows, columns=["number", "current", "max", "mean", "last_seen"]).set_index("number")


def pair_counts(draws: pd.DataFrame, top: int | None = 20) -> pd.DataFrame:
    """Coppie di numeri uscite insieme più spesso."""
    counts: dict[tuple[int, int], int] = {}
    for row in draws[NUMBER_COLUMNS].itertuples(index=False):
        for pair in combinations(sorted(row), 2):
            counts[pair] = counts.get(pair, 0) + 1
    df = pd.DataFrame([(a, b, c) for (a, b), c in counts.items()], columns=["a", "b", "count"])
    df = df.sort_values(["count", "a", "b"], ascending=[False, True, True], ignore_index=True)
    return df.head(top) if top else df


def shape(draws: pd.DataFrame) -> pd.DataFrame:
    """Caratteristiche di ogni sestina: somma, pari, bassi (≤45), coppie consecutive."""
    numbers = np.sort(draws[NUMBER_COLUMNS].to_numpy(), axis=1)
    return pd.DataFrame(
        {
            "id": draws["id"],
            "sum": numbers.sum(axis=1),
            "even": (numbers % 2 == 0).sum(axis=1),
            "low": (numbers <= MAX_NUMBER // 2).sum(axis=1),
            "consecutive": (np.diff(numbers, axis=1) == 1).sum(axis=1),
        }
    )
