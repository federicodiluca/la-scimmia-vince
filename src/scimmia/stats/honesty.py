"""La parte onesta: verificare se quello che "sembra" è davvero qualcosa.

Ogni funzione restituisce sia il numero grezzo (quello che ti mostrerebbe un sito di
pronostici) sia il confronto con il puro caso.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats

from scimmia.models import MAX_NUMBER, NUMBERS_PER_DRAW
from scimmia.stats.descriptive import frequency, frequency_by, hit_matrix

P_HIT = NUMBERS_PER_DRAW / MAX_NUMBER  # probabilità che un dato numero sia nella sestina: 1/15


@dataclass(frozen=True)
class UniformityResult:
    """Chi-quadro sulle frequenze: p alto = compatibile con un'urna equa."""

    draws: int
    expected_per_number: float
    chi2: float
    p_value: float
    most: int
    most_count: int
    least: int
    least_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def uniformity(draws: pd.DataFrame, column: str | None = None) -> UniformityResult:
    counts = frequency(draws, column)
    chi2, p = stats.chisquare(counts.to_numpy())
    return UniformityResult(
        draws=len(draws),
        expected_per_number=float(counts.mean()),
        chi2=float(chi2),
        p_value=float(p),
        most=int(counts.idxmax()),
        most_count=int(counts.max()),
        least=int(counts.idxmin()),
        least_count=int(counts.min()),
    )


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """p-value corretti per confronti multipli (False Discovery Rate)."""
    p = np.asarray(p_values, dtype=float)
    n = p.size
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1)
    out = np.empty(n)
    out[order] = adjusted
    return out


def fake_discoveries(draws: pd.DataFrame, by: str, alpha: float = 0.05) -> dict:
    """Caccia alle correlazioni tra numero e gruppo (anno, giorno, settimana…).

    Per ogni coppia (numero, gruppo) un test binomiale: "il 17 esce troppo il martedì?".
    Con centinaia di test, circa il 5% risulta "significativo" per puro caso: lo mostriamo
    prima e dopo la correzione di Benjamini-Hochberg.
    """
    table = frequency_by(draws, by)
    draws_per_group = table.sum(axis=0) / NUMBERS_PER_DRAW
    rows = []
    for group, n_draws in draws_per_group.items():
        for number, count in table[group].items():
            expected = n_draws * P_HIT
            p = stats.binomtest(int(count), int(n_draws), P_HIT).pvalue
            rows.append((number, group, int(count), expected, count / expected if expected else np.nan, p))
    cells = pd.DataFrame(rows, columns=["number", "group", "count", "expected", "ratio", "p_value"])
    cells["p_adjusted"] = benjamini_hochberg(cells["p_value"].to_numpy())

    naive = cells[cells["p_value"] < alpha].sort_values("p_value")
    survivors = cells[cells["p_adjusted"] < alpha]
    return {
        "by": by,
        "tests": len(cells),
        "alpha": alpha,
        "expected_false_positives": round(len(cells) * alpha, 1),
        "naive_discoveries": len(naive),
        "survivors_after_correction": len(survivors),
        "chi2_independence_p": float(stats.chi2_contingency(table[table.sum(axis=1) > 0].to_numpy())[1]),
        "best_fake": naive.head(10).round(4).to_dict(orient="records"),
    }


def delay_fallacy(draws: pd.DataFrame, buckets: tuple[int, ...] = (0, 10, 25, 50, 75, 100, 150)) -> pd.DataFrame:
    """Il mito del ritardatario: un numero "in ritardo" esce più spesso?

    Per ogni estrazione e ogni numero guardiamo il suo ritardo *prima* dell'estrazione
    e se poi è uscito. Se il mito fosse vero, la frequenza di uscita crescerebbe con il
    ritardo; in realtà resta ferma intorno a 1/15.
    """
    hits = hit_matrix(draws)
    n_draws = hits.shape[0]
    delay = np.zeros(MAX_NUMBER, dtype=int)
    delays_before = np.empty_like(hits, dtype=int)
    for i in range(n_draws):
        delays_before[i] = delay
        delay = np.where(hits[i], 0, delay + 1)

    # scartiamo le prime estrazioni: all'inizio i ritardi sono artificialmente bassi
    warmup = 200
    d = delays_before[warmup:].ravel()
    h = hits[warmup:].ravel()
    edges = [*buckets, np.inf]
    rows = []
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (d >= low) & (d < high)
        n = int(mask.sum())
        k = int(h[mask].sum())
        if n == 0:
            continue
        ci = stats.binomtest(k, n, P_HIT).proportion_ci(confidence_level=0.95)
        label = f"{low}+" if high == np.inf else f"{low}-{int(high) - 1}"
        rows.append((label, n, k, k / n, ci.low, ci.high, P_HIT))
    return pd.DataFrame(rows, columns=["delay", "opportunities", "hits", "hit_rate", "ci_low", "ci_high", "expected"])
