import numpy as np
import pandas as pd
import pytest

from scimmia.sources.meteo import moon_phase, sky, temperature_band
from scimmia.stats import honesty as hs
from tests.test_stats import make_draws


@pytest.mark.parametrize(
    ("day", "phase"),
    [
        ("2024-04-08", "luna nuova"),  # eclissi totale di sole in Nord America
        ("2024-04-23", "luna piena"),
        ("2024-04-15", "primo quarto"),
        ("2000-01-21", "luna piena"),  # eclissi totale di luna
    ],
)
def test_moon_phase_known_dates(day, phase):
    assert moon_phase(pd.Timestamp(day)) == phase


def test_sky_and_temperature():
    assert sky(pd.Series({"precipitation": 3.0, "sunshine_s": 40000, "daylight_s": 43000})) == "pioggia"
    assert sky(pd.Series({"precipitation": 0.0, "sunshine_s": 40000, "daylight_s": 43000})) == "sole"
    assert sky(pd.Series({"precipitation": 0.2, "sunshine_s": 5000, "daylight_s": 43000})) == "nuvoloso"
    assert [temperature_band(t) for t in (5, 12, 25, 35)] == ["sotto i 12 °C", "12-20 °C", "20-28 °C", "oltre 28 °C"]


def test_global_correction_is_stricter_than_per_family():
    rng = np.random.default_rng(3)
    draws = make_draws([tuple(rng.choice(np.arange(1, 91), 6, replace=False)) for _ in range(2000)])
    labels = pd.Series(rng.choice(["a", "b", "c"], len(draws)), name="assurdo")
    result = hs.fake_discoveries_all(draws, ["weekday", "month", labels])
    assert result["tests"] == sum(f["tests"] for f in result["families"])
    assert [f["by"] for f in result["families"]] == ["weekday", "month", "assurdo"]
    assert result["survivors_after_correction"] <= result["survivors_family"]


def test_nazionale_labels(tmp_path):
    from scimmia.sources.nazionale import match_labels, result

    assert [result(2, 0), result(1, 1), result(0, 3)] == ["vittoria", "pareggio", "sconfitta"]
    path = tmp_path / "italia.csv"
    path.write_text(
        "date,opponent,goals_for,goals_against,tournament,home\n"
        "2021-07-11,England,1,1,UEFA Euro,False\n"
        "2021-07-06,Spain,1,1,UEFA Euro,False\n",
        encoding="utf-8",
    )
    dates = pd.Series(pd.to_datetime(["2021-07-06", "2021-07-08", "2021-07-11"]))
    assert match_labels(dates, path).tolist() == ["pareggio", "nessuna partita", "pareggio"]
