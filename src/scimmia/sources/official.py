"""Archivio ufficiale su superenalotto.it (dal 2009 in poi).

Due tipi di pagina, entrambe renderizzate lato server:
- mensile  /archivio-estrazioni/{anno}/{mese}          -> sestina, jolly, superstar
- dettaglio /archivio-estrazioni/concorso-{n}/{gg-mese-aaaa} -> quote, vincitori, montepremi
"""

from __future__ import annotations

import re
import time
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from scimmia.models import Draw, DrawDetail, PrizeTier

SOURCE = "superenalotto.it"
BASE_URL = "https://www.superenalotto.it/archivio-estrazioni"
FIRST_YEAR = 2009

MONTHS = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]  # fmt: skip

_ROW = "superenalotto-extraction-archive__details__table"
_TIER = "superenalotto-extraction__table-details__item__content__table__body__row"
_POOL = "superenalotto-extraction__prize__content__table__row"
_LABEL = re.compile(r"(\d+)\D+?del\s+(\d{1,2})\s+([A-Za-zÀ-ú]+)\s+(\d{4})", re.IGNORECASE)


def month_url(year: int, month: int) -> str:
    return f"{BASE_URL}/{year}/{MONTHS[month - 1]}"


def _parse_label(text: str) -> tuple[int, date]:
    """'Concorso N° 140 del 1 Settembre 2026' -> (140, date(2026, 9, 1))."""
    m = _LABEL.search(" ".join(text.split()))
    if not m:
        raise ValueError(f"etichetta concorso non riconosciuta: {text!r}")
    contest, day, month_name, year = m.groups()
    return int(contest), date(int(year), MONTHS.index(month_name.lower()) + 1, int(day))


def _ints(parent: Tag, css_class: str) -> list[int]:
    texts = (s.get_text(strip=True) for s in parent.find_all(class_=css_class))
    return [int(t) for t in texts if t.isdigit()]


def parse_month_page(html: str) -> list[tuple[Draw, str]]:
    """Restituisce le estrazioni già avvenute nel mese, con l'URL della pagina di dettaglio.

    I concorsi futuri compaiono come "In programmazione" senza numeri e vengono saltati.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for tr in soup.find_all("tr", class_=f"{_ROW}__row"):
        label = tr.find(class_=f"{_ROW}__body__label")
        numbers = _ints(tr, f"{_ROW}__combination__text")
        jolly = _ints(tr, f"{_ROW}__jolly__text")
        if label is None or not numbers or not jolly:
            continue
        contest, day = _parse_label(label.get_text(" "))
        superstar = _ints(tr, f"{_ROW}__superstar__text")
        link = tr.find("a", class_="js-detail-link")
        draw = Draw(
            date=day,
            contest=contest,
            numbers=tuple(numbers),
            jolly=jolly[0],
            superstar=superstar[0] if superstar else None,
            source=SOURCE,
        )
        results.append((draw, link["href"] if link else ""))
    return results


def _euro(text: str) -> float | None:
    """'201.314,74 €' -> 201314.74; '-' -> None."""
    digits = re.sub(r"[^\d,]", "", text)
    return float(digits.replace(",", ".")) if digits else None


def _game_for(category: str) -> str:
    if category.lower().startswith("punti"):
        return "superenalotto"
    if "stella" in category.lower():
        return "superstar"
    return "immediate"


def parse_detail_page(html: str, draw_id: str) -> DrawDetail:
    soup = BeautifulSoup(html, "html.parser")

    tiers = []
    for tr in soup.find_all("tr", class_=_TIER):
        left = tr.find(class_=f"{_TIER}__left")
        middle = tr.find(class_=f"{_TIER}__middle")
        right = tr.find(class_=f"{_TIER}__right")
        if not (left and middle and right):
            continue
        category = " ".join(left.get_text().split())
        tiers.append(
            PrizeTier(
                game=_game_for(category),
                category=category,
                winners=int(re.sub(r"\D", "", middle.get_text()) or 0),
                amount_eur=_euro(right.get_text()),
            )
        )

    pool: dict[str, float | None] = {}
    for tr in soup.find_all("tr", class_=_POOL):
        left = tr.find(class_=f"{_POOL}__left")
        right = tr.find(class_=f"{_POOL}__right")
        if left and right:
            pool[" ".join(left.get_text().split()).lower()] = _euro(right.get_text())

    def pick(prefix: str) -> float | None:
        return next((v for k, v in pool.items() if k.startswith(prefix)), None)

    return DrawDetail(
        draw_id=draw_id,
        pool_contest_eur=pick("del concorso"),
        jackpot_carryover_eur=pick("riporto jackpot"),
        pool_total_eur=pick("montepremi totale"),
        tiers=tuple(tiers),
    )


class OfficialClient:
    """Client HTTP educato: una richiesta alla volta, pausa tra le chiamate, retry."""

    def __init__(self, delay_s: float = 0.7, retries: int = 3) -> None:
        self.delay_s = delay_s
        self.retries = retries
        self._last = 0.0
        self._http = httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LaScimmiaVince/0.1; +https://github.com/federicodiluca/la-scimmia-vince)",
                "Accept-Language": "it-IT,it;q=0.9",
            },
        )

    def get(self, url: str) -> str | None:
        """HTML della pagina, oppure None se non esiste (404)."""
        for attempt in range(1, self.retries + 1):
            wait = self.delay_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self._http.get(url)
            except httpx.TransportError:
                if attempt == self.retries:
                    raise
                time.sleep(2**attempt)
                continue
            if r.status_code == 404:
                return None
            if r.status_code >= 500 and attempt < self.retries:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
            return r.content.decode("utf-8", errors="replace")
        return None

    def month(self, year: int, month: int) -> list[tuple[Draw, str]]:
        html = self.get(month_url(year, month))
        return parse_month_page(html) if html else []

    def detail(self, url: str, draw_id: str) -> DrawDetail | None:
        html = self.get(url)
        return parse_detail_page(html, draw_id) if html else None

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> OfficialClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
