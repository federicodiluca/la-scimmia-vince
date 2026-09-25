"""Archivio storico annuale scaricato da TuttoSuperenalotto.it (1997 - aprile 2022).

Il sito ora mette l'archivio completo dietro pagamento: questi file sono una copia
statica e servono per il periodo che la fonte ufficiale non copre (1997-2008).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from scimmia.models import Draw

SOURCE = "tuttosuperenalotto"
_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def parse_legacy_html(html: str) -> list[Draw]:
    soup = BeautifulSoup(html, "html.parser")
    draws = []
    for tr in soup.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) != 10 or not _DATE.match(cells[0]):
            continue
        # colonne: data, concorso, 6 numeri, jolly, superstar ("00" = non esisteva ancora)
        superstar = int(cells[9])
        draws.append(
            Draw(
                date=datetime.strptime(cells[0], "%d/%m/%Y").date(),
                contest=int(cells[1]),
                numbers=tuple(int(c) for c in cells[2:8]),
                jolly=int(cells[8]),
                superstar=superstar or None,
                source=SOURCE,
            )
        )
    return draws


def load_legacy_dir(directory: Path) -> list[Draw]:
    draws: list[Draw] = []
    for path in sorted(directory.glob("*.html")):
        draws.extend(parse_legacy_html(path.read_text(encoding="utf-8", errors="replace")))
    return sorted(draws, key=lambda d: d.date)
