"""Costruzione e aggiornamento incrementale dell'archivio."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scimmia.models import Draw
from scimmia.sources import legacy, official
from scimmia.sources.official import OfficialClient
from scimmia.store import LEGACY_DIR, Store

log = logging.getLogger(__name__)


def detail_url(draw: Draw) -> str:
    month = official.MONTHS[draw.date.month - 1]
    return f"{official.BASE_URL}/concorso-{draw.contest}/{draw.date.day:02d}-{month}-{draw.date.year}"


def months_between(start: date, end: date) -> Iterator[tuple[int, int]]:
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def import_legacy(store: Store, directory: Path = LEGACY_DIR) -> int:
    """Riempie con l'archivio legacy solo i concorsi che la fonte ufficiale non ha."""
    added = sum(store.add_draw(d) for d in legacy.load_legacy_dir(directory))
    log.info("legacy: %d estrazioni aggiunte", added)
    return added


@dataclass
class UpdateReport:
    months: int = 0
    new_draws: int = 0
    new_details: int = 0


def update_official(
    store: Store,
    client: OfficialClient,
    *,
    since: date | None = None,
    today: date | None = None,
    max_details: int | None = None,
    save_every: int = 50,
) -> UpdateReport:
    """Scarica dal sito ufficiale le estrazioni mancanti e le relative quote.

    Senza `since` riparte dal mese dell'ultima estrazione ufficiale già in archivio
    (o dal 2009 se l'archivio ufficiale è vuoto). I dati ufficiali sostituiscono
    quelli legacy dello stesso concorso.
    """
    today = today or date.today()
    if since is None:
        last = store.last_draw(official.SOURCE)
        since = last.date.replace(day=1) if last else date(official.FIRST_YEAR, 1, 1)

    report = UpdateReport()
    for year, month in months_between(since, today):
        rows = client.month(year, month)
        report.months += 1
        for draw, _url in rows:
            current = store.draws.get(draw.id)
            if current is None or current.source != official.SOURCE:
                store.add_draw(draw, overwrite=True)
                report.new_draws += current is None
        log.info("%d-%02d: %d estrazioni", year, month, len(rows))
        if report.months % 12 == 0:
            store.save()
    store.save()

    missing = sorted(
        (d for d in store.draws.values() if d.source == official.SOURCE and d.id not in store.details),
        key=lambda d: d.date,
    )
    if max_details is not None:
        missing = missing[:max_details]
    for i, draw in enumerate(missing, 1):
        detail = client.detail(detail_url(draw), draw.id)
        if detail is None:
            log.warning("dettaglio non trovato per %s (%s)", draw.id, detail_url(draw))
            continue
        store.add_detail(detail)
        report.new_details += 1
        if i % save_every == 0:
            log.info("dettagli: %d/%d", i, len(missing))
            store.save()
    store.save()
    return report


def check_sequence(store: Store) -> list[str]:
    """Buchi o salti nella numerazione dei concorsi di ogni anno, date fuori ordine."""
    problems = []
    by_year: dict[int, list[Draw]] = {}
    for d in store.draws.values():
        by_year.setdefault(d.date.year, []).append(d)
    for year, draws in sorted(by_year.items()):
        draws.sort(key=lambda d: d.contest)
        contests = [d.contest for d in draws]
        missing = sorted(set(range(1, contests[-1] + 1)) - set(contests))
        if missing:
            problems.append(f"{year}: concorsi mancanti {missing}")
        for a, b in zip(draws, draws[1:]):
            if b.date <= a.date:
                problems.append(f"{b.id}: data {b.date} non successiva a {a.id} ({a.date})")
    return problems


# differenze tra le fonti già verificate: vale il dato ufficiale
KNOWN_DIFFERENCES = {
    "2015-129": "TuttoSuperenalotto riporta 14 al posto di 13",
}


def compare_sources(store: Store, directory: Path = LEGACY_DIR) -> list[str]:
    """Differenze tra archivio legacy e ufficiale sui concorsi in comune."""
    problems = []
    for old in legacy.load_legacy_dir(directory):
        new = store.draws.get(old.id)
        if new is None or new.source != official.SOURCE or old.id in KNOWN_DIFFERENCES:
            continue
        for attr in ("date", "numbers", "jolly", "superstar"):
            a, b = getattr(old, attr), getattr(new, attr)
            if attr == "numbers":
                a, b = sorted(a), sorted(b)
            if a != b:
                problems.append(f"{old.id} {attr}: legacy={a} ufficiale={b}")
    return problems
