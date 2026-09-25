import numpy as np
import pandas as pd

from scimmia.simulate import TIERS, Game, payouts, run
from scimmia.stats.descriptive import hit_matrix


def make_game() -> Game:
    draws = pd.DataFrame(
        {
            "id": ["2020-001", "2020-002", "2020-003"],
            "date": pd.to_datetime(["2020-01-02", "2020-01-04", "2020-01-07"]),
            "n1": [1, 1, 1], "n2": [2, 2, 2], "n3": [3, 3, 3],
            "n4": [4, 4, 4], "n5": [5, 5, 5], "n6": [6, 6, 6],
            "jolly": [7, 8, 9],
        }
    )  # fmt: skip
    #                  2     3     4      5        5+1        6
    prizes = np.array(
        [
            [0.0, 20.0, 300.0, 30_000.0, 500_000.0, np.nan],  # 6 senza vincitori: quota ignota
            [5.0, 25.0, 350.0, 40_000.0, 600_000.0, 90_000_000.0],
            [5.0, 25.0, 350.0, 40_000.0, 600_000.0, 90_000_000.0],
        ]
    )
    return Game(draws, prizes, np.array([0.5, 1.0, 1.0]), hit_matrix(draws), draws, 0, "2020-002")


def test_payouts_categories():
    game = make_game()
    picks = np.array(
        [
            [1, 2, 3, 4, 5, 6],  # 6 centrati, ma senza vincitori: ignoto
            [1, 2, 3, 4, 5, 8],  # 5 + jolly (8)
            [1, 2, 40, 50, 60, 70],  # 2 centrati: 5 €
        ]
    )
    won, matched = payouts(game, picks)
    assert matched.tolist() == [6, 5, 2]
    assert np.isnan(won[0])
    assert won[1:].tolist() == [600_000.0, 5.0]


def test_two_matches_paid_nothing_before_rule_change():
    game = make_game()
    picks = np.array([[1, 2, 40, 50, 60, 70]] * 3)
    won, _ = payouts(game, picks)
    assert won.tolist() == [0.0, 5.0, 5.0]


def test_run_balance_and_unknown_jackpot():
    game = make_game()
    result = run(game, "x", "x", np.array([[1, 2, 3, 4, 5, 6], [1, 2, 3, 40, 50, 60], [80, 81, 82, 83, 84, 85]]))
    assert result.spent == 2.5
    assert result.won == 25.0
    assert result.unknown_jackpots == 1
    assert result.balance.tolist() == [-0.5, 23.5, 22.5]
    assert TIERS[-1] == "Punti 6"
