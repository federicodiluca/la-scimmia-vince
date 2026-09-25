"""Esporta le statistiche in JSON, pronte per il sito."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scimmia.stats import descriptive as ds
from scimmia.stats import honesty as hs
from scimmia.store import DATA_DIR, load_draws_df


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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=_default), encoding="utf-8")
    return path


def _series(s: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in s.items()}


def export_all(out: str | Path = "build/stats", data_dir: Path = DATA_DIR) -> list[Path]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    draws = load_draws_df(data_dir)
    last = draws.iloc[-1]
    written = []

    written.append(
        _write(
            out,
            "summary",
            {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "draws": len(draws),
                "first_date": draws["date"].iloc[0].date().isoformat(),
                "last_draw": {
                    "id": last["id"],
                    "date": last["date"].date().isoformat(),
                    "numbers": [int(last[c]) for c in ds.NUMBER_COLUMNS],
                    "jolly": int(last["jolly"]),
                    "superstar": None if pd.isna(last["superstar"]) else int(last["superstar"]),
                },
            },
        )
    )

    written.append(
        _write(
            out,
            "frequency",
            {
                "numbers": _series(ds.frequency(draws)),
                "jolly": _series(ds.frequency(draws, "jolly")),
                "superstar": _series(ds.frequency(draws, "superstar")),
                "by_year": {str(y): _series(col) for y, col in ds.frequency_by(draws, "year").items()},
                "by_weekday": {str(w): _series(col) for w, col in ds.frequency_by(draws, "weekday").items()},
                "by_isoweek": {str(w): _series(col) for w, col in ds.frequency_by(draws, "isoweek").items()},
            },
        )
    )

    delays = ds.delays(draws).reset_index()
    written.append(_write(out, "delays", delays.to_dict(orient="records")))
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
                "fake_discoveries": [hs.fake_discoveries(draws, by) for by in ["weekday", "month", "year", "isoweek"]],
                "delay_fallacy": hs.delay_fallacy(draws).to_dict(orient="records"),
            },
        )
    )
    return written
