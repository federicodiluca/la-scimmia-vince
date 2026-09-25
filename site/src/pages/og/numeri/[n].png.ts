import type { APIRoute } from "astro";
import { frequency, numbers, numberStats } from "../../../lib/data";
import { dec, int } from "../../../lib/format";
import { pngResponse, renderCard } from "../../../lib/og";

export function getStaticPaths() {
  return numbers.map((n) => ({ params: { n: String(n.number) } }));
}

export const GET: APIRoute = async ({ params }) => {
  const n = Number(params.n);
  const s = numberStats(n);
  const png = await renderCard({
    ball: n,
    kicker: "SuperEnalotto · statistiche oneste",
    title: `Il numero ${n}`,
    lines: [
      `Uscito ${int(s.count)} volte, attese ${dec(frequency.band.expected, 0)}`,
      `Ritardo: ${int(s.delay.current)} · record: ${int(s.delay.max)}`,
      "Alla prossima: sempre 1 su 15.",
    ],
  });
  return pngResponse(png);
};
