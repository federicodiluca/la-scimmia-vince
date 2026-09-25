"""Riga di comando: `scimmia <comando>`."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from scimmia import update
from scimmia.sources.official import OfficialClient
from scimmia.store import LEGACY_DIR, Store


def cmd_update(args: argparse.Namespace) -> int:
    store = Store.load()
    if args.legacy:
        update.import_legacy(store)
    since = date(args.since, 1, 1) if args.since else None
    with OfficialClient(delay_s=args.delay) as client:
        report = update.update_official(store, client, since=since, max_details=args.max_details)
    print(
        f"mesi letti: {report.months} · nuove estrazioni: {report.new_draws} · "
        f"nuovi dettagli: {report.new_details} · totale archivio: {len(store.draws)}"
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    # il caricamento valida ogni estrazione (6 numeri distinti in 1..90, jolly fuori sestina…)
    store = Store.load()
    problems = update.check_sequence(store)
    if LEGACY_DIR.exists():
        problems += update.compare_sources(store)
    else:
        print("archivio legacy non presente in locale: salto il confronto tra fonti")
    for p in problems:
        print(p)
    print(f"{len(store.draws)} estrazioni valide · {len(problems)} problemi")
    return 1 if problems else 0


def cmd_stats(args: argparse.Namespace) -> int:
    from scimmia.stats.export import export_all

    written = export_all(args.out)
    for path in written:
        print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scimmia", description="La Scimmia Vince 🐒")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("update", help="scarica le estrazioni mancanti dal sito ufficiale")
    p.add_argument("--since", type=int, help="riscarica dall'anno indicato (es. 2009 per il backfill)")
    p.add_argument("--legacy", action="store_true", help="reimporta anche l'archivio legacy")
    p.add_argument("--max-details", type=int, help="limita le pagine di dettaglio scaricate")
    p.add_argument("--delay", type=float, default=0.7, help="secondi tra una richiesta e l'altra")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("check", help="confronta archivio legacy e ufficiale")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("stats", help="calcola le statistiche e le esporta in JSON")
    p.add_argument("--out", default="build/stats", help="cartella di destinazione")
    p.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
