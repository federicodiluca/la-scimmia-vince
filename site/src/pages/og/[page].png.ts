import type { APIRoute } from "astro";
import { frequency, honesty, simulation, summary } from "../../lib/data";
import { dec, int, pct } from "../../lib/format";
import { pngResponse, renderCard, type Card } from "../../lib/og";

const late = honesty.delay_fallacy.filter((b) => ["75-99", "100-149", "150+"].includes(b.delay));
const lateRate = late.reduce((s, b) => s + b.hits, 0) / late.reduce((s, b) => s + b.opportunities, 0);

const CARDS: Record<string, Card> = {
  home: {
    kicker: `SuperEnalotto · ${int(summary.draws)} estrazioni dal 1997`,
    title: "Il caso non ha memoria.",
    lines: [
      `${frequency.band.outside} numeri su 90 fuori dalla fascia del caso.`,
      `${int(honesty.fake_discoveries.naive_discoveries)} "scoperte", ${honesty.fake_discoveries.survivors_after_correction} vere.`,
      "La scimmia lo sa.",
    ],
  },
  ritardatari: {
    kicker: "Il mito del ritardatario",
    title: "Il ritardo non conta.",
    lines: [`Un numero in ritardo da 75+ estrazioni esce il ${pct(lateRate)}.`, `Uno qualsiasi: ${pct(6 / 90)}.`],
  },
  correlazioni: {
    kicker: "Correlazioni assurde",
    title: "Sole, luna, martedì.",
    lines: [
      `${int(honesty.fake_discoveries.tests)} confronti, ${int(honesty.fake_discoveries.naive_discoveries)} "scoperte".`,
      `Vere: ${honesty.fake_discoveries.survivors_after_correction}.`,
    ],
  },
  "se-avessi-giocato": {
    kicker: `Una colonna a ogni concorso dal ${new Date(simulation.first.date).getUTCFullYear()}`,
    title: "E se avessi giocato i tuoi numeri?",
    lines: [
      `${dec(simulation.spent, 0)} € spesi. La scimmia mediana ne recupera il ${pct(simulation.monkeys.returned["50"]!)}.`,
      "Scegli 6 numeri e scopri com'è andata.",
    ],
  },
  "smettere-di-giocare": {
    kicker: "Ludopatia · aiuto gratuito e anonimo",
    title: "Vuoi smettere di giocare?",
    lines: [`Su 100 € giocati ne tornano circa ${Math.round(100 * simulation.monkeys.returned["50"]!)}.`, "Telefono Verde ISS: 800 55 88 22."],
  },
};

export function getStaticPaths() {
  return Object.keys(CARDS).map((page) => ({ params: { page } }));
}

export const GET: APIRoute = async ({ params }) => pngResponse(await renderCard(CARDS[params.page!]!));
