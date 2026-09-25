import numpy as np
import pandas as pd
import pytest

from scimmia.stats import descriptive as ds
from scimmia.stats import honesty as hs


def make_draws(rows: list[tuple[int, ...]], start: str = "2020-01-07") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(rows), freq="2D")
    df = pd.DataFrame(rows, columns=ds.NUMBER_COLUMNS)
    df.insert(0, "date", dates)
    df.insert(0, "id", [f"{d.year}-{i:03d}" for i, d in enumerate(dates, 1)])
    df["jolly"] = 90
    df["superstar"] = pd.array([1] * len(rows), dtype="Int64")
    return df


@pytest.fixture
def random_draws() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return make_draws([tuple(rng.choice(np.arange(1, 91), 6, replace=False)) for _ in range(3000)])


def test_frequency_covers_all_numbers():
    draws = make_draws([(1, 2, 3, 4, 5, 6), (1, 10, 20, 30, 40, 50)])
    freq = ds.frequency(draws)
    assert len(freq) == 90
    assert freq[1] == 2 and freq[10] == 1 and freq[89] == 0
    assert freq.sum() == 12


def test_delays():
    draws = make_draws([(1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12), (1, 13, 14, 15, 16, 17)])
    d = ds.delays(draws)
    assert d.loc[1, "current"] == 0 and d.loc[1, "mean"] == 1
    assert d.loc[2, "current"] == 2
    assert d.loc[90, "current"] == 3 and pd.isna(d.loc[90, "last_seen"])


def test_frequency_by_weekday_sums_to_numbers_drawn():
    draws = make_draws([(1, 2, 3, 4, 5, 6)] * 7, start="2024-01-01")
    table = ds.frequency_by(draws, "weekday")
    assert table.to_numpy().sum() == 42
    assert table.loc[1].sum() == 7


def test_pairs_and_shape():
    draws = make_draws([(1, 2, 3, 4, 5, 6), (1, 2, 30, 40, 50, 60)])
    pairs = ds.pair_counts(draws, top=1)
    assert pairs.iloc[0][["a", "b", "count"]].tolist() == [1, 2, 2]
    shape = ds.shape(draws)
    assert shape.loc[0, "sum"] == 21 and shape.loc[0, "consecutive"] == 5 and shape.loc[0, "even"] == 3


def test_benjamini_hochberg_matches_manual():
    p = np.array([0.01, 0.04, 0.03, 0.5])
    assert np.allclose(hs.benjamini_hochberg(p), [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.5])


def test_random_data_has_no_real_correlations(random_draws):
    result = hs.fake_discoveries(random_draws, "weekday")
    assert result["naive_discoveries"] > 0  # il caso produce sempre qualche "scoperta"...
    assert result["survivors_after_correction"] <= 2  # ...che quasi mai sopravvive alla correzione


def test_delay_fallacy_is_flat_on_random_data(random_draws):
    table = hs.delay_fallacy(random_draws)
    well_sampled = table[table["opportunities"] > 5000]
    assert ((well_sampled["ci_low"] <= hs.P_HIT) & (hs.P_HIT <= well_sampled["ci_high"])).mean() >= 0.8
