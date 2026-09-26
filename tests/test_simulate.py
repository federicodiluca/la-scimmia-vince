import numpy as np
import pandas as pd

from scimmia.simulate import TIERS, Game, load_game, payouts, reference_cases, run
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


def test_run_balance_and_unknown_win():
    game = make_game()
    result = run(game, "x", "x", np.array([[1, 2, 3, 4, 5, 6], [1, 2, 3, 40, 50, 60], [80, 81, 82, 83, 84, 85]]))
    assert result.spent == 2.5
    assert result.won == 25.0
    assert result.unknown_wins == 1
    assert result.balance.tolist() == [-0.5, 23.5, 22.5]
    assert TIERS[-1] == "Punti 6"


def test_load_game_category_without_winners_is_unknown(tmp_path):
    (tmp_path / "draws.csv").write_text(
        "id,date,contest,n1,n2,n3,n4,n5,n6,jolly,superstar,source\n"
        "2016-157,2016-12-31,157,1,2,3,4,5,6,7,,test\n"
        "2017-001,2017-01-03,1,1,2,3,4,5,6,8,,test\n",
        encoding="utf-8",
    )
    rows = ["draw_id,game,category,winners,amount_eur"]
    for draw, two in [("2016-157", None), ("2017-001", (1000, 5.0))]:
        if two:
            rows.append(f"{draw},superenalotto,Punti 2,{two[0]},{two[1]}")
        rows += [
            f"{draw},superenalotto,Punti 3,100,25.0",
            f"{draw},superenalotto,Punti 4,10,350.0",
            f"{draw},superenalotto,Punti 5,0,",  # nessun vincitore: chi l'avesse fatto avrebbe vinto
            f"{draw},superenalotto,Punti 5+1,0,",
            f"{draw},superenalotto,Punti 6,1,50000000.0",
        ]
    (tmp_path / "prizes.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    game = load_game(tmp_path)
    assert game.prizes[0, 0] == 0.0  # il 2 non esisteva ancora: non è un premio
    assert game.prizes[1, 0] == 5.0
    assert np.isnan(game.prizes[:, 3]).all() and np.isnan(game.prizes[:, 4]).all()
    assert game.prizes[:, 5].tolist() == [50_000_000.0] * 2
    assert game.price.tolist() == [0.5, 1.0]
    assert game.price_change_id == "2017-001"


def test_reference_cases_cover_edge_cases():
    cases = reference_cases(make_game(), n_random=5)
    assert len(cases) == 5 + 1 + 2  # casuali, 1-6, i due 6 con vincitori (qui 5 e 5+1 hanno sempre la quota)
    six = next(c for c in cases if c["picks"] == [1, 2, 3, 4, 5, 6])
    assert six["unknown"] == 1 and six["won"] == 180_000_000.0
    assert all(len(set(c["picks"])) == 6 for c in cases)
