import type { APIRoute } from "astro";
import { simulation as sim } from "../../lib/data";
import { int, pct } from "../../lib/format";
import { pngResponse, renderStory } from "../../lib/og";

// L'immagine per le storie di Instagram: il simulatore "Se avessi giocato…", rifatto a ogni
// build con i dati dell'ultimo concorso
const c = sim.curves;
const firstYear = new Date(sim.first.date).getUTCFullYear();
// strategie sopra la fascia delle scimmie: meglio del 95% di loro
const beating = sim.strategies.filter((s) => s.monkeys_better < sim.players * 0.05).length;

export const GET: APIRoute = async () =>
  pngResponse(
    await renderStory({
      kicker: `Una colonna a ogni concorso dal ${firstYear}`,
      intro: [
        `${int(sim.draws)} concorsi, ${int(Math.round(sim.spent))} € spesi. Cinque strategie`,
        `da manuale contro ${int(sim.players)} scimmie che giocano a caso.`,
      ],
      years: [String(firstYear), String(new Date(sim.last.date).getUTCFullYear())],
      band: { low: c.monkeys["5"], mid: c.monkeys["50"], high: c.monkeys["95"] },
      strategies: Object.values(c.strategies),
      stats: [
        { value: pct(sim.monkeys.returned["50"]!), label: "dei soldi torna alla scimmia mediana" },
        {
          value: `${beating} su ${sim.strategies.length}`,
          label: beating === 1 ? "strategia batte le scimmie" : "strategie battono le scimmie",
        },
      ],
    }),
  );
