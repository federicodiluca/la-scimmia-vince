from datetime import date
from pathlib import Path

import pytest

from scimmia.models import Draw
from scimmia.sources.legacy import parse_legacy_html
from scimmia.sources.official import _euro, _parse_label, parse_detail_page, parse_month_page
from scimmia.update import detail_url, months_between

FIXTURES = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def test_month_page_skips_scheduled_draws():
    rows = parse_month_page(read("official_month_2026_settembre.html"))
    assert [d.contest for d, _ in rows] == list(range(140, 154))
    first, url = rows[0]
    assert first == Draw(date(2026, 9, 1), 140, (42, 47, 59, 64, 67, 71), 88, 75, "superenalotto.it")
    assert url == detail_url(first)


def test_detail_page_prizes_and_pool():
    detail = parse_detail_page(read("official_detail_2026_144.html"), "2026-144")
    assert detail.pool_total_eur == 225_421_031.24
    assert detail.jackpot_carryover_eur == 220_621_549.26
    tiers = {t.category: t for t in detail.tiers}
    assert tiers["Punti 6"].winners == 0 and tiers["Punti 6"].amount_eur is None
    assert tiers["Punti 4"].winners == 542 and tiers["Punti 4"].amount_eur == 377.21
    assert tiers["3 Stella"].game == "superstar"
    assert tiers["WinBox"].game == "immediate"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Concorso N° 140 del 1 Settembre 2026", (140, date(2026, 9, 1))),
        ("Concorso N� 7 del\n   15 gennaio 2009", (7, date(2009, 1, 15))),
    ],
)
def test_parse_label(text, expected):
    assert _parse_label(text) == expected


def test_euro():
    assert _euro("201.314,74 €") == 201314.74
    assert _euro("5,00 ��") == 5.0
    assert _euro("-") is None


def test_legacy_superstar_zero_means_missing():
    html = (
        "<table><tr><td>03/12/1997</td><td>01</td><td>20</td><td>36</td><td>39</td>"
        "<td>41</td><td>72</td><td>76</td><td>88</td><td>00</td></tr></table>"
    )
    [draw] = parse_legacy_html(html)
    assert draw.id == "1997-001"
    assert draw.superstar is None


def test_draw_validation():
    with pytest.raises(ValueError):
        Draw(date(2020, 1, 1), 1, (1, 2, 3, 4, 5, 5), 6, None, "x")
    with pytest.raises(ValueError):
        Draw(date(2020, 1, 1), 1, (1, 2, 3, 4, 5, 6), 6, None, "x")


def test_months_between_crosses_year():
    assert list(months_between(date(2025, 11, 20), date(2026, 2, 1))) == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]


def test_detail_page_skips_empty_tier_rows():
    row = "superenalotto-extraction__table-details__item__content__table__body__row"
    html = "".join(
        f'<table><tr class="{row}"><td class="{row}__left">{left}</td>'
        f'<td class="{row}__middle">{mid}</td><td class="{row}__right">{right}</td></tr></table>'
        for left, mid, right in [("Punti 3", "10", "25,00 €"), ("", "0", "-")]
    )
    detail = parse_detail_page(html, "2017-001")
    assert [t.category for t in detail.tiers] == ["Punti 3"]
