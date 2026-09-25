"""Simulatore "Se avessi giocato…": strategie contro scimmia, con le quote reali.

Regole della simulazione:
- una colonna (6 numeri) per concorso, dal primo concorso con le quote ufficiali (2009);
- vincita = quota reale pagata quel giorno per la categoria centrata (2, 3, 4, 5, 5+1, 6),
  al lordo delle tasse sulle vincite: un'ipotesi generosa verso il giocatore;
- costo della giocata: 0,50 € fino al cambio di regolamento, 1 € dal primo concorso che
  paga il "Punti 2" (gennaio 2017): la data è ricavata dai dati, non scritta a mano;
- se una strategia centra un 6 in un concorso senza vincitori non c'è una quota da
  usare: la vincita resta sconosciuta ed è segnalata a parte (non è mai successo).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from scimmia.models import MAX_NUMBER
from scimmia.stats.descriptive import NUMBER_COLUMNS, delays_before, hit_matrix
from scimmia.store import DATA_DIR, load_draws_df, load_prizes_df

# colonne della tabella premi: indice = numeri centrati (0..6), più il 5+1 in fondo
TIERS = ["Punti 2", "Punti 3", "Punti 4", "Punti 5", "Punti 5+1", "Punti 6"]
_TIER_INDEX = {2: 0, 3: 1, 4: 2, 5: 3, 6: 5}
FIVE_PLUS_ONE = 4


class NoPrizeData(Exception):
    """L'archivio non ha ancora quote ufficiali: il simulatore non può girare."""


@dataclass(frozen=True)
class Game:
    """Estrazioni con quote, allineate per indice."""

    draws: pd.DataFrame  # solo i concorsi con quote, ordinati
    prizes: np.ndarray  # (concorsi, 6) quota per categoria, 0 se nessuna quota, nan se 6 senza vincitori
    price: np.ndarray  # (concorsi,) costo di una colonna
    hits: np.ndarray  # (concorsi, 90) bool
    history: pd.DataFrame  # tutte le estrazioni dal 1997, per le strategie che guardano il passato
    offset: int  # indice in `history` del primo concorso di `draws`
    price_change_id: str | None


def load_game(data_dir=DATA_DIR) -> Game:
    history = load_draws_df(data_dir)
    prizes = load_prizes_df(data_dir)
    prizes = prizes[prizes["game"] == "superenalotto"]
    with_prizes = set(prizes["draw_id"])
    mask = history["id"].isin(with_prizes).to_numpy()
    if not mask.any():
        raise NoPrizeData("nessun concorso con quote: lanciare `scimmia update`")
    offset = int(np.argmax(mask))
    # serie continua di concorsi con quote (a backfill in corso si ferma al primo buco)
    gap = np.flatnonzero(~mask[offset:])
    end = offset + (int(gap[0]) if len(gap) else len(history) - offset)
    draws = history.iloc[offset:end].reset_index(drop=True)

    table = prizes.pivot_table(index="draw_id", columns="category", values="amount_eur", aggfunc="first")
    winners = prizes.pivot_table(index="draw_id", columns="category", values="winners", aggfunc="first")
    table = table.reindex(index=draws["id"], columns=TIERS)
    winners = winners.reindex(index=draws["id"], columns=TIERS)
    amounts = table.to_numpy(dtype=float, copy=True)  # con il copy-on-write di pandas la vista è in sola lettura
    # categoria inesistente all'epoca (es. Punti 2 prima del 2017) o senza vincitori: 0,
    # tranne il 6 senza vincitori, che resta ignoto (nan)
    no_quote = np.isnan(amounts)
    amounts[no_quote] = 0.0
    six = TIERS.index("Punti 6")
    amounts[:, six] = np.where(winners["Punti 6"].fillna(0).to_numpy() > 0, amounts[:, six], np.nan)

    has_two = winners["Punti 2"].notna().to_numpy()
    change = int(np.argmax(has_two)) if has_two.any() else len(draws)
    price = np.where(np.arange(len(draws)) >= change, 1.0, 0.5)

    return Game(
        draws=draws,
        prizes=amounts,
        price=price,
        hits=hit_matrix(draws),
        history=history,
        offset=offset,
        price_change_id=draws["id"].iloc[change] if change < len(draws) else None,
    )


def payouts(game: Game, picks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vincite e numeri centrati per giocate (…, concorsi, 6); restituisce (vincite, centrati)."""
    n = len(game.draws)
    idx = np.arange(n).reshape((1,) * (picks.ndim - 2) + (n, 1))
    matched = game.hits[idx, picks - 1].sum(axis=-1)
    jolly = game.draws["jolly"].to_numpy().reshape((1,) * (picks.ndim - 2) + (n, 1))
    has_jolly = (picks == jolly).any(axis=-1)

    tier = np.full(matched.shape, -1)
    for k, t in _TIER_INDEX.items():
        tier[matched == k] = t
    tier[(matched == 5) & has_jolly] = FIVE_PLUS_ONE

    rows = np.broadcast_to(np.arange(n), matched.shape)
    won = np.where(tier >= 0, game.prizes[rows, np.maximum(tier, 0)], 0.0)
    return won, matched


# ---- strategie: per ogni concorso, 6 numeri scelti con le sole informazioni precedenti ----


def _before_each_draw(game: Game) -> tuple[np.ndarray, np.ndarray]:
    """Conteggi e ritardi di ogni numero *prima* di ciascun concorso simulato."""
    all_hits = hit_matrix(game.history)
    counts = np.cumsum(all_hits, axis=0) - all_hits  # esclude il concorso stesso
    delays = delays_before(all_hits)
    end = game.offset + len(game.draws)
    return counts[game.offset : end], delays[game.offset : end]


def _top6(score: np.ndarray) -> np.ndarray:
    # a parità di punteggio vince il numero più basso: scelta deterministica e riproducibile
    order = np.lexsort((np.arange(MAX_NUMBER)[None, :].repeat(len(score), 0), -score), axis=-1)
    return np.sort(order[:, :6] + 1, axis=1)


def strategies(game: Game) -> dict[str, tuple[str, np.ndarray]]:
    counts, delays = _before_each_draw(game)
    last = game.history[NUMBER_COLUMNS].to_numpy()[game.offset - 1 : game.offset - 1 + len(game.draws)]
    fixed = np.tile(np.arange(1, 7), (len(game.draws), 1))
    return {
        "ritardatari": ("I 6 numeri più in ritardo", _top6(delays)),
        "caldi": ("I 6 numeri più usciti di sempre", _top6(counts)),
        "freddi": ("I 6 numeri meno usciti di sempre", _top6(-counts)),
        "ultima": ("La sestina dell'estrazione precedente", np.sort(last, axis=1)),
        "sempre_uguali": ("Sempre 1 2 3 4 5 6", fixed),
    }


def monkeys(game: Game, players: int, rng: np.random.Generator) -> np.ndarray:
    """Giocate casuali: (giocatori, concorsi, 6), 6 numeri distinti per concorso."""
    keys = rng.random((players, len(game.draws), MAX_NUMBER), dtype=np.float32)
    return np.sort(np.argpartition(keys, 6, axis=-1)[..., :6] + 1, axis=-1)


@dataclass
class Result:
    key: str
    label: str
    spent: float
    won: float
    unknown_jackpots: int
    best_win: float
    best_win_id: str | None
    matches: dict[int, int]
    balance: np.ndarray  # saldo cumulato concorso per concorso

    @property
    def returned(self) -> float:
        return self.won / self.spent if self.spent else 0.0


def run(game: Game, key: str, label: str, picks: np.ndarray) -> Result:
    won, matched = payouts(game, picks)
    unknown = int(np.isnan(won).sum())
    won = np.nan_to_num(won)
    best = int(np.argmax(won))
    return Result(
        key=key,
        label=label,
        spent=float(game.price.sum()),
        won=float(won.sum()),
        unknown_jackpots=unknown,
        best_win=float(won[best]),
        best_win_id=game.draws["id"].iloc[best] if won[best] > 0 else None,
        matches={k: int((matched == k).sum()) for k in range(7)},
        balance=np.cumsum(won - game.price),
    )


def simulate_all(game: Game, players: int = 1000, seed: int = 90, chunk: int = 25) -> tuple[list[Result], np.ndarray]:
    """Risultati delle strategie e saldi cumulati delle scimmie (giocatori, concorsi).

    Le scimmie sono generate a blocchi: tutte insieme occuperebbero gigabyte di memoria.
    """
    results = [run(game, key, label, picks) for key, (label, picks) in strategies(game).items()]
    rng = np.random.default_rng(seed)
    balances = []
    for start in range(0, players, chunk):
        won, _ = payouts(game, monkeys(game, min(chunk, players - start), rng))
        balances.append(np.cumsum(np.nan_to_num(won) - game.price, axis=1))
    return results, np.concatenate(balances)
