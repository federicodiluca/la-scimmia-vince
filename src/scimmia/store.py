"""Archivio su CSV versionati nel repo: leggibili, diffabili, caricabili ovunque.

data/superenalotto/
  draws.csv   una riga per estrazione
  prizes.csv  una riga per (estrazione, categoria di premio)
  pools.csv   montepremi e jackpot per estrazione
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from scimmia.models import Draw, DrawDetail, PrizeTier

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "superenalotto"
LEGACY_DIR = ROOT / "data" / "raw" / "tuttosuperenalotto"

DRAW_COLUMNS = ["id", "date", "contest", "n1", "n2", "n3", "n4", "n5", "n6", "jolly", "superstar", "source"]
PRIZE_COLUMNS = ["draw_id", "game", "category", "winners", "amount_eur"]
POOL_COLUMNS = ["draw_id", "pool_contest_eur", "jackpot_carryover_eur", "pool_total_eur"]


def _fmt(value: object) -> str:
    return "" if value is None else str(value)


def _opt_int(value: str) -> int | None:
    return int(value) if value else None


def _opt_float(value: str) -> float | None:
    return float(value) if value else None


@dataclass
class Store:
    directory: Path = DATA_DIR
    draws: dict[str, Draw] = field(default_factory=dict)
    details: dict[str, DrawDetail] = field(default_factory=dict)

    @property
    def draws_path(self) -> Path:
        return self.directory / "draws.csv"

    @property
    def prizes_path(self) -> Path:
        return self.directory / "prizes.csv"

    @property
    def pools_path(self) -> Path:
        return self.directory / "pools.csv"

    # ---- lettura -------------------------------------------------------

    @classmethod
    def load(cls, directory: Path = DATA_DIR) -> Store:
        store = cls(directory)
        if store.draws_path.exists():
            with store.draws_path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    draw = Draw(
                        date=date.fromisoformat(row["date"]),
                        contest=int(row["contest"]),
                        numbers=tuple(int(row[f"n{i}"]) for i in range(1, 7)),
                        jolly=int(row["jolly"]),
                        superstar=_opt_int(row["superstar"]),
                        source=row["source"],
                    )
                    store.draws[draw.id] = draw

        tiers: dict[str, list[PrizeTier]] = {}
        if store.prizes_path.exists():
            with store.prizes_path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    tiers.setdefault(row["draw_id"], []).append(
                        PrizeTier(row["game"], row["category"], int(row["winners"]), _opt_float(row["amount_eur"]))
                    )
        if store.pools_path.exists():
            with store.pools_path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    store.details[row["draw_id"]] = DrawDetail(
                        draw_id=row["draw_id"],
                        pool_contest_eur=_opt_float(row["pool_contest_eur"]),
                        jackpot_carryover_eur=_opt_float(row["jackpot_carryover_eur"]),
                        pool_total_eur=_opt_float(row["pool_total_eur"]),
                        tiers=tuple(tiers.get(row["draw_id"], [])),
                    )
        return store

    # ---- scrittura -----------------------------------------------------

    def add_draw(self, draw: Draw, *, overwrite: bool = False) -> bool:
        """Aggiunge l'estrazione; True se è nuova o è stata sostituita."""
        if draw.id in self.draws and not overwrite:
            return False
        self.draws[draw.id] = draw
        return True

    def add_detail(self, detail: DrawDetail) -> None:
        self.details[detail.draw_id] = detail

    def save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        draws = sorted(self.draws.values(), key=lambda d: (d.date, d.contest))
        with self.draws_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(DRAW_COLUMNS)
            for d in draws:
                w.writerow([d.id, d.date.isoformat(), d.contest, *d.numbers, d.jolly, _fmt(d.superstar), d.source])

        details = sorted(self.details.values(), key=lambda d: d.draw_id)
        with self.pools_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(POOL_COLUMNS)
            for d in details:
                w.writerow([d.draw_id, _fmt(d.pool_contest_eur), _fmt(d.jackpot_carryover_eur), _fmt(d.pool_total_eur)])
        with self.prizes_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(PRIZE_COLUMNS)
            for d in details:
                for t in d.tiers:
                    w.writerow([d.draw_id, t.game, t.category, t.winners, _fmt(t.amount_eur)])

    # ---- viste pandas per le analisi ----------------------------------

    def last_draw(self, source: str | None = None) -> Draw | None:
        draws = [d for d in self.draws.values() if source is None or d.source == source]
        return max(draws, key=lambda d: (d.date, d.contest), default=None)


def load_draws_df(directory: Path = DATA_DIR) -> pd.DataFrame:
    """Estrazioni come DataFrame ordinato per data (colonne n1..n6, jolly, superstar)."""
    df = pd.read_csv(directory / "draws.csv", parse_dates=["date"], dtype={"superstar": "Int64"})
    return df.sort_values(["date", "contest"]).reset_index(drop=True)


def load_prizes_df(directory: Path = DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(directory / "prizes.csv")


def load_pools_df(directory: Path = DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(directory / "pools.csv")
