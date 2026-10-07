Quanto avresti vinto al SuperEnalotto giocando sempre gli stessi numeri? Ho costruito un simulatore per rispondere con i dati veri.

Si chiama «Se avessi giocato…», è nel mio progetto La Scimmia Vince. Scegli 6 numeri e il sito li gioca a ogni concorso dal 2 gennaio 2009: 2.925 concorsi, con le quote vere pagate ogni sera e il prezzo della schedina giusto (cambia nel 2017). Per esempio, giocando sempre 1-2-3-4-5-6 si spendono 2.298,50 € e se ne recuperano 472,90.

Poi c'è il confronto: 1.000 «scimmie» che scelgono 6 numeri a caso a ogni concorso. La scimmia mediana recupera il 29% di quello che spende, e solo 2 scimmie su 1.000 chiudono in attivo. Le strategie da manuale del giocatore (ritardatari, numeri caldi e freddi…) restano dentro la fascia delle scimmie: quello che sembra funzionare è caso.

Qualche scelta tecnica:
• il calcolo avviene nel browser, con le stesse regole del motore Python che genera i dati: i numeri non partono da nessuna parte
• il sito è Astro, tutto statico; l'archivio si aggiorna con una GitHub Action dopo ogni concorso
• i grafici sono SVG generati in fase di build, leggibili anche senza JavaScript e con una tabella dati accanto

Non è un invito a giocare: è il contrario. Nessuna pubblicità legata al gioco, nessun link affiliato, e il sito ha anche una pagina su come smettere.

lascimmiavince.federicodiluca.com/se-avessi-giocato
Codice: github.com/federicodiluca/la-scimmia-vince

#dataviz #astro #typescript #python #statistica
