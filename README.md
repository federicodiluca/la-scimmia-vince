<img src="site/public/favicon.svg" alt="" width="72" align="right">

# La Scimmia Vince

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

In `data/meteo/roma.csv` c'è il meteo giornaliero di Roma dal 1997 (temperatura massima, pioggia, ore di sole e
di luce) dall'[archivio storico di Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api), usato per
le "correlazioni assurde". In `data/nazionale/italia.csv` ci sono le partite dell'Italia dal 1997, dal dataset
[international_results](https://github.com/martj42/international_results) (CC0).

Una GitHub Action (`.github/workflows/update-data.yml`) scarica le nuove estrazioni dopo ogni
concorso (mar, gio, ven, sab) e fa il commit dei dati.

> Fino al 2009 la sestina era ricavata dai primi estratti di sei ruote del Lotto; dal luglio 2009 il
> SuperEnalotto ha un'estrazione propria. La superstar esiste da marzo 2006.

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

## Sito

Il sito è in `site/` ([Astro](https://astro.build), tutto statico) ed è pubblicato su
<https://federicodiluca.github.io/la-scimmia-vince/>. Le pagine (home, 90 schede numero, archivio per anno,
ritardatari, correlazioni, metodo) si generano dai JSON prodotti da `scimmia stats`. I grafici sono SVG generati
in fase di build: si leggono anche senza JavaScript e hanno sempre una tabella dati accanto.

Serve Node ≥ 22.12 (vedi `site/.nvmrc`).

```bash
uv run scimmia stats --out site/src/data/generated   # dati per il sito
cd site
npm ci
npm run dev                                           # http://localhost:4321/la-scimmia-vince/
npm run build                                         # icone PNG + sito statico in site/dist
```

Deploy: `.github/workflows/deploy-site.yml` a ogni push su `main`, e dopo ogni aggiornamento dei dati.

## Statistiche

`src/scimmia/stats/descriptive.py`: frequenze (in assoluto, per anno, mese, giorno, settimana),
ritardi, coppie, forma della sestina (somma, pari/dispari, alti/bassi, consecutivi).

`src/scimmia/stats/honesty.py`: la parte che ci distingue.

- **uniformità**: chi-quadro sulle frequenze, per capire se sono compatibili con un'urna equa
- **false scoperte**: per ogni coppia numero × gruppo (es. "il 17 esce di più il martedì?") un test
  binomiale, con il conteggio delle "scoperte" prima e dopo la correzione di Benjamini-Hochberg
- **mito del ritardatario**: frequenza di uscita di un numero in funzione del suo ritardo; se il mito
  fosse vero la curva salirebbe, invece è piatta a 1/15
- **correlazioni assurde**: calendario, meteo di Roma, fasi lunari e partite della Nazionale, con la correzione fatta su *tutti* i
  confronti insieme; quella per singolo gruppo lascia passare falsi positivi (es. "l'85 con la luna nuova")

`src/scimmia/simulate.py`: il simulatore "Se avessi giocato…". Strategie (ritardatari, caldi, freddi, ultima
sestina, sempre 1-2-3-4-5-6) contro 1.000 scimmie che giocano a caso, con le quote reali di ogni concorso dal 2009.

## Roadmap

- [x] Fase 1: dati aggiornati automaticamente e motore statistico
- [x] Fase 2: sito Astro su GitHub Pages (pagine per numero, anno, ritardatari, correlazioni) con favicon e icone a tema
- [x] Fase 3: simulatore "se avessi giocato…", strategie contro scimmia, correlazioni con meteo e luna
- [x] Card condivisibili, pagine per ogni estrazione, partite della Nazionale
- [ ] Poi: Sanremo
- [ ] Fase 4: Lotto (bot Telegram in stand-by)

## Licenza

- **Codice**: [MIT](LICENSE)
- **Dati** (`data/`): [CC BY 4.0](data/LICENSE.md). Puoi riusarli citando la fonte. Le singole fonti (risultati
  ufficiali, Open-Meteo, international_results) restano dei rispettivi titolari: i dettagli sono in
  [data/LICENSE.md](data/LICENSE.md).

---

Il gioco può causare dipendenza patologica. Questo progetto non invita a giocare, anzi.
