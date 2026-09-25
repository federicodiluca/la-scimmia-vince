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
from scimmia.stats.descriptive import delays_before, frequency, frequency_by, hit_matrix

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


def _cells(draws: pd.DataFrame, by: str | pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Un test binomiale per ogni coppia (numero, gruppo): "il 17 esce troppo il martedì?"."""
    table = frequency_by(draws, by)
    draws_per_group = table.sum(axis=0) / NUMBERS_PER_DRAW
    rows = []
    for group, n_draws in draws_per_group.items():
        for number, count in table[group].items():
            expected = n_draws * P_HIT
            p = stats.binomtest(int(count), int(n_draws), P_HIT).pvalue
            rows.append((number, group, int(count), expected, count / expected if expected else np.nan, p))
    cells = pd.DataFrame(rows, columns=["number", "group", "count", "expected", "ratio", "p_value"])
    return cells, table, draws_per_group


def _summary(by: str, cells: pd.DataFrame, table: pd.DataFrame, draws_per_group: pd.Series, alpha: float) -> dict:
    naive = cells[cells["p_value"] < alpha].sort_values("p_value")
    return {
        "by": by,
        "groups": {str(g): int(n) for g, n in draws_per_group.round().astype(int).items()},
        "tests": len(cells),
        "alpha": alpha,
        "expected_false_positives": round(len(cells) * alpha, 1),
        "naive_discoveries": len(naive),
        "survivors_family": int((cells["p_family"] < alpha).sum()),
        "survivors_after_correction": int((cells["p_adjusted"] < alpha).sum()),
        "chi2_independence_p": float(stats.chi2_contingency(table[table.sum(axis=1) > 0].to_numpy())[1]),
        "best_fake": naive.head(10).round(6).to_dict(orient="records"),
    }


def fake_discoveries(draws: pd.DataFrame, by: str | pd.Series, alpha: float = 0.05) -> dict:
    """Caccia alle correlazioni tra numero e gruppo (anno, giorno, settimana, meteo…).

    Con centinaia di test, circa il 5% risulta "significativo" per puro caso: lo mostriamo
    prima e dopo la correzione di Benjamini-Hochberg sui test di questo raggruppamento.
    """
    return fake_discoveries_all(draws, [by], alpha)["families"][0]


def fake_discoveries_all(draws: pd.DataFrame, groupings: list[str | pd.Series], alpha: float = 0.05) -> dict:
    """Come `fake_discoveries`, ma su più raggruppamenti insieme.

    La correzione onesta è su *tutti* i confronti fatti: correggendo famiglia per famiglia,
    più famiglie si aggiungono, più è facile che un falso positivo passi (`survivors_family`).
    """
    families = []
    for by in groupings:
        name = by if isinstance(by, str) else str(by.name)
        cells, table, per_group = _cells(draws, by)
        cells["p_family"] = benjamini_hochberg(cells["p_value"].to_numpy())
        families.append((name, cells, table, per_group))
    everything = pd.concat([c for _, c, _, _ in families], keys=range(len(families)))
    everything["p_adjusted"] = benjamini_hochberg(everything["p_value"].to_numpy())
    out = []
    for i, (name, cells, table, per_group) in enumerate(families):
        cells["p_adjusted"] = everything.loc[i, "p_adjusted"].to_numpy()
        out.append(_summary(name, cells, table, per_group, alpha))
    return {
        "tests": len(everything),
        "naive_discoveries": int((everything["p_value"] < alpha).sum()),
        "expected_false_positives": round(len(everything) * alpha, 1),
        "survivors_family": sum(f["survivors_family"] for f in out),
        "survivors_after_correction": int((everything["p_adjusted"] < alpha).sum()),
        "families": out,
    }


def delay_fallacy(draws: pd.DataFrame, buckets: tuple[int, ...] = (0, 10, 25, 50, 75, 100, 150)) -> pd.DataFrame:
    """Il mito del ritardatario: un numero "in ritardo" esce più spesso?

    Per ogni estrazione e ogni numero guardiamo il suo ritardo *prima* dell'estrazione
    e se poi è uscito. Se il mito fosse vero, la frequenza di uscita crescerebbe con il
    ritardo; in realtà resta ferma intorno a 1/15.
    """
    hits = hit_matrix(draws)
    before = delays_before(hits)

    # scartiamo le prime estrazioni: all'inizio i ritardi sono artificialmente bassi
    warmup = 200
    d = before[warmup:].ravel()
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
