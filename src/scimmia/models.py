from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

MIN_NUMBER = 1
MAX_NUMBER = 90
NUMBERS_PER_DRAW = 6


@dataclass(frozen=True)
class Draw:
    """Una estrazione del SuperEnalotto.

    `contest` è il numero di concorso, che riparte da 1 ogni anno.
    `superstar` è None prima della sua introduzione (fine 2006).
    """

    date: date
    contest: int
    numbers: tuple[int, ...]
    jolly: int
    superstar: int | None
    source: str

    def __post_init__(self) -> None:
        if len(self.numbers) != NUMBERS_PER_DRAW:
            raise ValueError(f"{self.id}: attesi 6 numeri, trovati {self.numbers}")
        if len(set(self.numbers)) != NUMBERS_PER_DRAW:
            raise ValueError(f"{self.id}: numeri duplicati {self.numbers}")
        for n in (*self.numbers, self.jolly):
            if not MIN_NUMBER <= n <= MAX_NUMBER:
                raise ValueError(f"{self.id}: numero fuori range {n}")
        if self.jolly in self.numbers:
            raise ValueError(f"{self.id}: jolly {self.jolly} già nella sestina")
        if self.superstar is not None and not MIN_NUMBER <= self.superstar <= MAX_NUMBER:
            raise ValueError(f"{self.id}: superstar fuori range {self.superstar}")

    @property
    def id(self) -> str:
        return f"{self.date.year}-{self.contest:03d}"


@dataclass(frozen=True)
class PrizeTier:
    """Una categoria di premio: quanti vincitori e quanto ha pagato ciascuno."""

    game: str  # "superenalotto" | "superstar" | "immediate"
    category: str  # es. "Punti 5+1", "3 Stella", "WinBox"
    winners: int
    amount_eur: float | None  # None quando non ci sono vincitori ("-")


@dataclass(frozen=True)
class DrawDetail:
    """Quote e montepremi di un concorso (disponibili dalla fonte ufficiale)."""

    draw_id: str
    pool_contest_eur: float | None = None
    jackpot_carryover_eur: float | None = None
    pool_total_eur: float | None = None
    tiers: tuple[PrizeTier, ...] = field(default_factory=tuple)
