"""Esporta le statistiche in JSON, pronte per il sito."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from scimmia.stats import descriptive as ds
from scimmia.stats import honesty as hs
from scimmia.sources import meteo, nazionale
from scimmia.store import DATA_DIR, METEO_PATH, NAZIONALE_PATH, load_draws_df, load_pools_df, load_prizes_df


def _default(value: object) -> object:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if np.isnan(value) else round(float(value), 6)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    raise TypeError(f"non serializzabile: {type(value)}")


def _write(out: Path, name: str, payload: object) -> Path:
    path = out / f"{name}.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_default, allow_nan=False), encoding="utf-8"
    )
    return path


def _series(s: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in s.items()}


def _draw_record(row: pd.Series) -> dict:
    return {
        "id": row["id"],
        "date": row["date"].date().isoformat(),
        "n": [int(row[c]) for c in ds.NUMBER_COLUMNS],
        "j": int(row["jolly"]),
        "s": None if pd.isna(row["superstar"]) else int(row["superstar"]),
    }


def _jackpot(draws: pd.DataFrame, data_dir: Path) -> dict | None:
    """Montepremi dell'ultimo concorso e ultimo "6" (dalle quote ufficiali, dal 2009)."""
    try:
        pools = load_pools_df(data_dir)
        prizes = load_prizes_df(data_dir)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None
    if pools.empty:
        return None
    dates = draws.set_index("id")["date"]
    last_pool = pools.loc[pools["draw_id"].map(dates).idxmax()]
    sixes = prizes[(prizes["category"] == "Punti 6") & (prizes["winners"] > 0)]
    last_six = None
    if not sixes.empty:
        six = sixes.loc[sixes["draw_id"].map(dates).idxmax()]
        last_six = {
            "id": six["draw_id"],
            "date": dates[six["draw_id"]].date().isoformat(),
            "winners": int(six["winners"]),
            "amount_eur": float(six["amount_eur"]),
            "draws_since": int((draws["date"] > dates[six["draw_id"]]).sum()),
        }
    return {
        "draw_id": last_pool["draw_id"],
        "pool_total_eur": last_pool["pool_total_eur"],
        "carryover_eur": last_pool["jackpot_carryover_eur"],
        "last_six": last_six,
    }


def _details(data_dir: Path) -> dict:
    """Quote e montepremi per concorso: {id: {pool, carry, tiers: [[gioco, categoria, vincitori, quota]]}}."""
    try:
        pools = load_pools_df(data_dir)
        prizes = load_prizes_df(data_dir)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return {}
    out: dict[str, dict] = {
        row.draw_id: {"pool": _num(row.pool_total_eur), "carry": _num(row.jackpot_carryover_eur), "tiers": []}
        for row in pools.itertuples(index=False)
    }
    for row in prizes.itertuples(index=False):
        if row.draw_id in out:
            out[row.draw_id]["tiers"].append([row.game, row.category, int(row.winners), _num(row.amount_eur)])
    return out


def _num(value: object) -> float | None:
    return None if pd.isna(value) else float(value)


def _band(n_draws: int, confidence: float = 0.95) -> dict:
    """Intervallo in cui cade il conteggio di un numero, per puro caso, nel 95% dei casi."""
    tail = (1 - confidence) / 2
    return {
        "expected": n_draws * hs.P_HIT,
        "low": int(stats.binom.ppf(tail, n_draws, hs.P_HIT)),
        "high": int(stats.binom.ppf(1 - tail, n_draws, hs.P_HIT)),
        "confidence": confidence,
    }


def _numbers(draws: pd.DataFrame) -> list[dict]:
    freq = ds.frequency(draws)
    jolly = ds.frequency(draws, "jolly")
    superstar = ds.frequency(draws, "superstar")
    by_year = ds.frequency_by(draws, "year")
    delays = ds.delays(draws)
    pairs = ds.pair_counts(draws, top=None)
    ranks = freq.rank(ascending=False, method="min").astype(int)

    records = []
    for n in ds.ALL_NUMBERS:
        mine = pairs[(pairs["a"] == n) | (pairs["b"] == n)].head(5)
        partners = [
            {"number": int(r.b if r.a == n else r.a), "count": int(r.count)} for r in mine.itertuples(index=False)
        ]
        d = delays.loc[n]
        records.append(
            {
                "number": int(n),
                "count": int(freq[n]),
                "rank": int(ranks[n]),
                "jolly": int(jolly[n]),
                "superstar": int(superstar[n]),
                "delay": {
                    "current": int(d["current"]),
                    "max": int(d["max"]),
                    "mean": d["mean"],
                    "last_seen": d["last_seen"],
                },
                "by_year": _series(by_year.loc[n]),
                "partners": partners,
            }
        )
    return records


def _simulation(data_dir: Path, players: int = 1000, points: int = 240) -> tuple[dict, list, list] | None:
    """Strategie contro scimmie, tabella per il simulatore nel browser e casi per verificarlo."""
    from scimmia import simulate

    try:
        game = simulate.load_game(data_dir)
    except (FileNotFoundError, pd.errors.EmptyDataError, simulate.NoPrizeData):
        return None  # archivio senza quote: niente simulatore (qualsiasi altro errore deve emergere)
    results, monkeys = simulate.simulate_all(game, players=players)
    n = len(game.draws)
    idx = np.unique(np.linspace(0, n - 1, min(points, n)).round().astype(int))
    dates = game.draws["date"].dt.date.astype(str).to_numpy()
    final = monkeys[:, -1]
    spent = float(game.price.sum())

    summary = {
        "first": {"id": game.draws["id"].iloc[0], "date": dates[0]},
        "last": {"id": game.draws["id"].iloc[-1], "date": dates[-1]},
        "draws": n,
        "players": len(monkeys),
        "spent": spent,
        "price_change": (
            {"id": game.price_change_id, "date": dates[game.draws["id"].tolist().index(game.price_change_id)]}
            if game.price_change_id
            else None
        ),
        "monkeys": {
            "returned": {str(p): float(1 + np.percentile(final, p) / spent) for p in (5, 25, 50, 75, 95)},
            "best_returned": float(1 + final.max() / spent),
            "in_profit": int((final > 0).sum()),
            "final_sorted": np.sort(final).round(0).astype(int).tolist(),
        },
        "strategies": [
            {
                "key": r.key,
                "label": r.label,
                "spent": r.spent,
                "won": round(r.won, 2),
                "returned": r.returned,
                "best_win": r.best_win,
                "best_win_id": r.best_win_id,
                "matches": {str(k): v for k, v in r.matches.items()},
                "unknown_wins": r.unknown_wins,
                "monkeys_better": int((final > r.balance[-1]).sum()),
            }
            for r in results
        ],
        "curves": {
            "dates": dates[idx].tolist(),
            "monkeys": {str(p): np.percentile(monkeys[:, idx], p, axis=0).round(2).tolist() for p in (5, 50, 95)},
            "strategies": {r.key: r.balance[idx].round(2).tolist() for r in results},
        },
    }

    prizes = np.where(np.isnan(game.prizes), -1, game.prizes).round(2)
    table = [
        [row.id, dates[i], [int(getattr(row, c)) for c in ds.NUMBER_COLUMNS], int(row.jolly), float(game.price[i]), prizes[i].tolist()]
        for i, row in enumerate(game.draws.itertuples(index=False))
    ]
    return summary, table, simulate.reference_cases(game)


def _context_labels(
    draws: pd.DataFrame, meteo_path: Path = METEO_PATH, nazionale_path: Path = NAZIONALE_PATH
) -> list[pd.Series]:
    """Etichette "assurde" per ogni estrazione: fase lunare e, se disponibili, meteo di Roma e Nazionale."""
    labels = [draws["date"].map(meteo.moon_phase).rename("luna")]
    if nazionale_path.exists():
        labels.append(nazionale.match_labels(draws["date"], nazionale_path))
    if meteo_path.exists():
        weather = pd.read_csv(meteo_path, parse_dates=["date"]).set_index("date")
        day = weather.reindex(draws["date"]).reset_index(drop=True)
        known = day["tmax"].notna()
        labels += [
            day[known].apply(meteo.sky, axis=1).reindex(day.index).rename("meteo"),
            day.loc[known, "tmax"].map(meteo.temperature_band).reindex(day.index).rename("temperatura"),
        ]
    return labels


def export_all(out: str | Path = "build/stats", data_dir: Path = DATA_DIR, meteo_path: Path = METEO_PATH) -> list[Path]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    draws = load_draws_df(data_dir)
    written = []

    written.append(
        _write(
            out,
            "summary",
            {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "draws": len(draws),
                "first_date": draws["date"].iloc[0].date().isoformat(),
                "last_draw": _draw_record(draws.iloc[-1]),
                "jackpot": _jackpot(draws, data_dir),
            },
        )
    )

    freq = ds.frequency(draws)
    band = _band(len(draws))
    written.append(
        _write(
            out,
            "frequency",
            {
                "numbers": _series(freq),
                "band": {**band, "outside": int(((freq < band["low"]) | (freq > band["high"])).sum())},
                "jolly": _series(ds.frequency(draws, "jolly")),
                "superstar": _series(ds.frequency(draws, "superstar")),
                "by_year": {str(y): _series(col) for y, col in ds.frequency_by(draws, "year").items()},
                "by_weekday": {str(w): _series(col) for w, col in ds.frequency_by(draws, "weekday").items()},
                "by_isoweek": {str(w): _series(col) for w, col in ds.frequency_by(draws, "isoweek").items()},
            },
        )
    )

    written.append(_write(out, "numbers", _numbers(draws)))
    # per ogni estrazione anche il ritardo che avevano i suoi 6 numeri prima di uscire
    before = ds.delays_before(ds.hit_matrix(draws))
    records = []
    for i, (_, row) in enumerate(draws.iterrows()):
        rec = _draw_record(row)
        rec["d"] = [int(before[i, n - 1]) for n in rec["n"]]
        records.append(rec)
    written.append(_write(out, "draws", records))
    details = _details(data_dir)
    if details:
        written.append(_write(out, "details", details))
    written.append(_write(out, "pairs", ds.pair_counts(draws, top=50).to_dict(orient="records")))

    shape = ds.shape(draws)
    written.append(
        _write(
            out,
            "shape",
            {col: _series(shape[col].value_counts().sort_index()) for col in ["sum", "even", "low", "consecutive"]},
        )
    )

    written.append(
        _write(
            out,
            "honesty",
            {
                "uniformity": {
                    "numbers": hs.uniformity(draws).to_dict(),
                    "jolly": hs.uniformity(draws, "jolly").to_dict(),
                    "superstar": hs.uniformity(draws, "superstar").to_dict(),
                },
                "fake_discoveries": hs.fake_discoveries_all(
                    draws, ["weekday", "month", "year", "isoweek", *_context_labels(draws, meteo_path)]
                ),
                "delay_fallacy": hs.delay_fallacy(draws).to_dict(orient="records"),
            },
        )
    )

    sim = _simulation(data_dir)
    if sim is not None:
        summary, table, cases = sim
        written.append(_write(out, "simulation", summary))
        # [id, data, sestina, jolly, prezzo, quote 2/3/4/5/5+1/6 (-1 = 6 senza vincitori)]
        written.append(_write(out, "game", {"tiers": ["2", "3", "4", "5", "5+1", "6"], "draws": table}))
        # risultati di riferimento: `npm test` nel sito controlla che il simulatore JS dia gli stessi
        written.append(_write(out, "simulator-check", cases))
    return written
