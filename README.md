# La Scimmia Vince 🐒

Statistiche **oneste** (e un po' ironiche) sulle estrazioni del SuperEnalotto dal 1997 a oggi.

I siti dei giocatori mostrano numeri "caldi", "freddi" e ritardatari. Qui partiamo dagli stessi dati
e verifichiamo quello che sembra una regolarità: quasi sempre è il caso che fa il suo lavoro.
Una scimmia che gioca numeri a caso fa esattamente come chi segue le "strategie".

## Dati

| Periodo | Fonte | Contenuto |
| --- | --- | --- |
| 1997 → 2008 | archivio storico di TuttoSuperenalotto.it, scaricato nel 2022 | sestina, jolly, superstar |
| 2009 → oggi | [superenalotto.it](https://www.superenalotto.it/archivio-estrazioni) | sestina, jolly, superstar, quote, vincitori, montepremi |

I file HTML originali di TuttoSuperenalotto non sono ridistribuiti: nel repo ci sono solo i risultati
estratti (in `draws.csv`, con `source = tuttosuperenalotto`). Chi li ha in locale li mette in
`data/raw/tuttosuperenalotto/`; in quel caso `scimmia check` confronta anche le due fonti sul
periodo in cui si sovrappongono (2009 → aprile 2022). Senza, controlla comunque l'integrità
dell'archivio: estrazioni valide, nessun concorso mancante, date in ordine.

L'archivio normalizzato è versionato in `data/superenalotto/`:

- `draws.csv`: una riga per estrazione (`id` = `anno-concorso`, es. `2026-144`)
- `prizes.csv`: vincitori e quota per ogni categoria (`superenalotto`, `superstar`, `immediate`; per `immediate` l'importo è il totale erogato, non la quota unitaria)
- `pools.csv`: montepremi del concorso, riporto jackpot, montepremi totale

Una GitHub Action (`.github/workflows/update-data.yml`) scarica le nuove estrazioni dopo ogni
concorso (mar, gio, ven, sab) e fa il commit dei dati.

> Fino al 2009 la sestina era ricavata dai primi estratti di sei ruote del Lotto; dal luglio 2009 il
> SuperEnalotto ha un'estrazione propria. La superstar esiste dalla fine del 2006.

## Uso

Serve [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # ambiente e dipendenze
uv run scimmia update            # scarica le estrazioni mancanti
uv run scimmia update --since 2009            # riscarica tutto il periodo ufficiale (lento: ~2 ore)
uv run scimmia check             # integrità archivio (+ confronto col legacy se presente)
uv run scimmia stats --out build/stats        # esporta le statistiche in JSON per il sito
uv run pytest                    # test
```

`Analysis.ipynb` è il banco di prova per esplorazioni e verifiche veloci.

## Statistiche

`src/scimmia/stats/descriptive.py`: frequenze (in assoluto, per anno, mese, giorno, settimana),
ritardi, coppie, forma della sestina (somma, pari/dispari, alti/bassi, consecutivi).

`src/scimmia/stats/honesty.py`: la parte che ci distingue.

- **uniformità**: chi-quadro sulle frequenze, per capire se sono compatibili con un'urna equa
- **false scoperte**: per ogni coppia numero × gruppo (es. "il 17 esce di più il martedì?") un test
  binomiale, con il conteggio delle "scoperte" prima e dopo la correzione di Benjamini-Hochberg
- **mito del ritardatario**: frequenza di uscita di un numero in funzione del suo ritardo; se il mito
  fosse vero la curva salirebbe, invece è piatta a 1/15

## Roadmap

- [x] Fase 1: dati aggiornati automaticamente e motore statistico
- [ ] Fase 2: sito Astro su GitHub Pages (pagine per numero, anno, estrazione) con favicon e icone a tema
- [ ] Fase 3: simulatore "se avessi giocato…", strategie contro scimmia, correlazioni col meteo, card condivisibili
- [ ] Fase 4: Lotto (bot Telegram in stand-by)

---

Il gioco può causare dipendenza patologica. Questo progetto non invita a giocare, anzi.
