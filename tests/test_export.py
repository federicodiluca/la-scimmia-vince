import json
from datetime import date, timedelta

import numpy as np

from scimmia.models import Draw
from scimmia.stats.export import export_all
from scimmia.store import Store


def test_export_all_writes_site_json(tmp_path):
    rng = np.random.default_rng(7)
    store = Store(tmp_path / "data")
    start = date(2020, 1, 2)
    for i in range(400):
        picks = rng.choice(np.arange(1, 91), 7, replace=False)
        day = start + timedelta(days=2 * i)
        contest = sum(1 for d in store.draws.values() if d.date.year == day.year) + 1
        store.add_draw(Draw(day, contest, tuple(sorted(int(x) for x in picks[:6])), int(picks[6]), 1, "test"))
    store.save()

    written = export_all(tmp_path / "out", data_dir=store.directory)
    names = {p.stem for p in written}
    assert {"summary", "frequency", "numbers", "draws", "pairs", "shape", "honesty"} <= names

    summary = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert summary["draws"] == 400
    assert summary["jackpot"] is None  # niente quote in questo archivio

    numbers = json.loads((tmp_path / "out" / "numbers.json").read_text(encoding="utf-8"))
    assert [n["number"] for n in numbers] == list(range(1, 91))
    assert sum(n["count"] for n in numbers) == 400 * 6

    band = json.loads((tmp_path / "out" / "frequency.json").read_text(encoding="utf-8"))["band"]
    assert band["low"] < band["expected"] < band["high"]
