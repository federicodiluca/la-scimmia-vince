"""Meteo giornaliero di Roma (dove si tengono le estrazioni) dall'archivio storico di Open-Meteo.

https://open-meteo.com/en/docs/historical-weather-api: gratuito, senza chiave, dati dal 1940
(rianalisi ERA5, con qualche giorno di ritardo sugli ultimi giorni).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import httpx
import pandas as pd

URL = "https://archive-api.open-meteo.com/v1/archive"
ROME = {"latitude": 41.89, "longitude": 12.49}
DAILY = ["temperature_2m_max", "precipitation_sum", "sunshine_duration", "daylight_duration"]
COLUMNS = ["date", "tmax", "precipitation", "sunshine_s", "daylight_s"]


def fetch_daily(start: date, end: date) -> pd.DataFrame:
    params = {
        **ROME,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY),
        "timezone": "Europe/Rome",
    }
    r = httpx.get(URL, params=params, timeout=60)
    r.raise_for_status()
    daily = r.json()["daily"]
    df = pd.DataFrame({"date": daily["time"], **{c: daily[k] for c, k in zip(COLUMNS[1:], DAILY)}})
    # gli ultimi giorni possono non essere ancora disponibili: li riscaricheremo la prossima volta
    return df.dropna(subset=["tmax", "precipitation"]).reset_index(drop=True)


def update_meteo(path: Path, first: date, today: date | None = None) -> int:
    """Aggiunge al CSV i giorni mancanti; restituisce quanti giorni sono stati aggiunti."""
    today = today or date.today()
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    start = date.fromisoformat(old["date"].iloc[-1]) + timedelta(days=1) if len(old) else first
    if start > today:
        return 0
    new = fetch_daily(start, today)
    if new.empty:
        return 0
    merged = pd.concat([old, new]).drop_duplicates("date", keep="last").sort_values("date")
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(path, index=False, lineterminator="\n", float_format="%.2f")
    return len(merged) - len(old)


# ---- classificazioni per le "correlazioni assurde" -----------------------------


def sky(row: pd.Series) -> str:
    if row["precipitation"] >= 1.0:
        return "pioggia"
    if row["daylight_s"] and row["sunshine_s"] / row["daylight_s"] >= 0.7:
        return "sole"
    return "nuvoloso"


def temperature_band(tmax: float) -> str:
    if tmax < 12:
        return "sotto i 12 °C"
    if tmax < 20:
        return "12-20 °C"
    if tmax < 28:
        return "20-28 °C"
    return "oltre 28 °C"


SYNODIC_MONTH = 29.530588853
_NEW_MOON = pd.Timestamp("2000-01-06 18:14", tz="UTC")  # luna nuova di riferimento
MOON_PHASES = [
    "luna nuova",
    "luna crescente",
    "primo quarto",
    "gibbosa crescente",
    "luna piena",
    "gibbosa calante",
    "ultimo quarto",
    "luna calante",
]


def moon_phase(day: pd.Timestamp) -> str:
    """Fase lunare alle 20:00 di Roma (ora dell'estrazione), in 8 spicchi."""
    at = pd.Timestamp(day.date()).tz_localize("Europe/Rome") + pd.Timedelta(hours=20)
    age = ((at - _NEW_MOON).total_seconds() / 86400) % SYNODIC_MONTH
    return MOON_PHASES[math.floor((age / SYNODIC_MONTH) * 8 + 0.5) % 8]
