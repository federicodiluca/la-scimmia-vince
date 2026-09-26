// Grafico del saldo di una giocata contro la fascia delle scimmie, disegnato nel browser.
// Stessa grammatica di BalancePanel.astro (fascia 5°-95°, mediana, serie blu), ma con il
// dominio che si adatta alla giocata: se hai fatto 6 la fascia si schiaccia sullo zero, ed è giusto così.
import { niceStep } from "./svg";

const intf = new Intl.NumberFormat("it-IT", { useGrouping: "always" });
const compact = new Intl.NumberFormat("it-IT", { notation: "compact", maximumFractionDigits: 1 });
const eur = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0, useGrouping: "always" });

const tick = (t: number) => {
  if (t === 0) return "0 €";
  const abs = Math.abs(t);
  return `${t > 0 ? "+" : "−"}${abs >= 100_000 ? compact.format(abs) : intf.format(abs)} €`;
};

export function balanceChart(opts: {
  dates: string[];
  values: number[];
  band: { low: number[]; mid: number[]; high: number[] };
  label: string;
  /** larghezza reale in pixel: il grafico si disegna 1:1, così il testo resta leggibile sul telefono */
  width: number;
}): string {
  const { dates, values, band, label } = opts;
  const W = Math.max(280, Math.round(opts.width));
  const H = W < 480 ? 220 : 260;
  const all = [...values, ...band.low, ...band.high, 0];
  const pad = (Math.max(...all) - Math.min(...all)) * 0.06 || 1;
  const lo = Math.min(...all) - pad;
  const hi = Math.max(...all) + pad;
  const step = niceStep(hi - lo, 4);
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) ticks.push(Math.abs(t) < step / 1e6 ? 0 : t);
  // margine sinistro su misura dell'etichetta più lunga ("+300 Mln €"), ~7,5 px a carattere
  const m = { l: 14 + 7.5 * Math.max(...ticks.map((t) => tick(t).length)), r: 12, t: 12, b: 28 };
  const pw = W - m.l - m.r;
  const ph = H - m.t - m.b;
  const x = (i: number) => m.l + (i / (dates.length - 1)) * pw;
  const y = (v: number) => m.t + ((hi - v) / (hi - lo)) * ph;
  const pts = (vs: number[]) => vs.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
  const line = (vs: number[]) => "M" + pts(vs).join("L");
  const area = `M${pts(band.high).join("L")}L${pts(band.low).reverse().join("L")}Z`;

  const years = [...new Set(dates.map((d) => d.slice(0, 4)))];
  const every = W < 420 ? 4 : 3;
  const yearTicks = years
    .filter((yr) => (Number(yr) - Number(years[0])) % every === 1) // non sul bordo sinistro, dove ci sono gli importi
    .map((yr) => ({ yr, i: dates.findIndex((d) => d.startsWith(yr)) }));
  const last = values.length - 1;
  const zoneStep = Math.max(1, Math.round(dates.length / (W / 12)));
  const zones = dates.map((_, i) => i).filter((i) => i % zoneStep === 0);

  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${label}: saldo finale ${eur.format(values[last]!)}, scimmia mediana ${eur.format(band.mid[last]!)}">
    ${ticks
      .map(
        (t) => `<line class="${t === 0 ? "zero" : "grid"}" x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}"/>
        <text class="tick" x="${m.l - 6}" y="${y(t)}" dy="0.32em" text-anchor="end">${tick(t)}</text>`,
      )
      .join("")}
    ${yearTicks.map(({ yr, i }) => `<text class="tick" x="${x(i)}" y="${H - 6}" text-anchor="middle">${yr}</text>`).join("")}
    <path class="band" d="${area}"/>
    <path class="mid" d="${line(band.mid)}"/>
    <path class="series" d="${line(values)}"/>
    <circle class="end" cx="${x(last)}" cy="${y(values[last]!)}" r="5"/>
    ${zones
      .map((i, k) => {
        const next = zones[k + 1] ?? dates.length - 1;
        return `<rect class="hit" x="${x(i)}" width="${Math.max(1, x(next) - x(i))}" y="${m.t}" height="${ph}"
          data-tip="${dates[i]}: i tuoi numeri ${eur.format(values[i]!)} · scimmia mediana ${eur.format(band.mid[i]!)}"/>`;
      })
      .join("")}
  </svg>`;
}
