// Immagini Open Graph (1200×630) generate in fase di build: SVG → PNG con sharp.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import sharp from "sharp";

// dopo il bundle import.meta.url punta dentro dist/: la build gira sempre dalla cartella site/
const monkey = readFileSync(join(process.cwd(), "public", "favicon.svg"), "utf-8")
  .replace(/^<svg[^>]*>/, "")
  .replace(/<\/svg>\s*$/, "");

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export interface Card {
  kicker: string;
  title: string;
  lines: string[];
  ball?: number;
}

export async function renderCard({ kicker, title, lines, ball }: Card): Promise<Buffer> {
  const font = "DejaVu Sans, Segoe UI, Arial, sans-serif";
  const textX = ball ? 390 : 90;
  const titleSize = ball ? 72 : title.length > 22 ? 64 : 84;
  const lineSize = ball ? 34 : 38;
  // con la pallina il testo occupa più spazio: scimmia più piccola, in basso a destra
  const monkeyAt = ball ? "translate(1095 455) rotate(-8) scale(1.7) translate(-32 -32)" : "translate(1000 330) rotate(-8) scale(2.9) translate(-32 -32)";
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#f9f9f7"/>
  <rect x="0" y="560" width="1200" height="70" fill="#f2c230"/>
  <g transform="${monkeyAt}">${monkey}</g>
  ${
    ball
      ? `<circle cx="215" cy="290" r="130" fill="#f2c230"/><circle cx="215" cy="290" r="130" fill="none" stroke="#b8860b" stroke-width="6"/>
         <text x="215" y="290" dy="0.35em" text-anchor="middle" font-family="${font}" font-weight="800" font-size="130" fill="#3d2f00">${ball}</text>`
      : ""
  }
  <text x="${textX}" y="150" font-family="${font}" font-weight="700" font-size="30" fill="#52514e" letter-spacing="2">${esc(kicker.toUpperCase())}</text>
  <text x="${textX}" y="${150 + titleSize + 20}" font-family="${font}" font-weight="800" font-size="${titleSize}" fill="#0b0b0b">${esc(title)}</text>
  ${lines
    .map(
      (l, i) =>
        `<text x="${textX}" y="${150 + titleSize + 90 + i * (lineSize + 14)}" font-family="${font}" font-size="${lineSize}" fill="#52514e">${esc(l)}</text>`,
    )
    .join("")}
  <text x="90" y="605" font-family="${font}" font-weight="800" font-size="30" fill="#3d2f00">La Scimmia Vince</text>
  <text x="1110" y="605" text-anchor="end" font-family="${font}" font-size="28" fill="#3d2f00">il caso non ha memoria</text>
</svg>`;
  return sharp(Buffer.from(svg)).png({ compressionLevel: 9, palette: true }).toBuffer();
}

export function pngResponse(png: Buffer): Response {
  return new Response(new Uint8Array(png), { headers: { "Content-Type": "image/png" } });
}

export interface Story {
  kicker: string;
  intro: [string, string];
  years: [string, string];
  /** saldo cumulato nel tempo: fascia delle scimmie (5°-95° percentile), mediana, strategie */
  band: { low: number[]; mid: number[]; high: number[] };
  strategies: number[][];
  stats: { value: string; label: string }[];
}

/**
 * L'immagine per le storie di Instagram (1080×1920), del link «condividi» nel footer: il
 * simulatore "Se avessi giocato…", con il grafico del saldo come nella pagina. Instagram di
 * una condivisione prende solo l'immagine, quindi il link è scritto in grande. Il contenuto
 * importante sta tra y 250 e 1670: sopra e sotto le storie coprono con barra e risposta.
 */
export async function renderStory({ kicker, intro, years, band, strategies, stats }: Story): Promise<Buffer> {
  const font = "DejaVu Sans, Segoe UI, Arial, sans-serif";

  // il grafico, nella scheda bianca
  const cx = 100, cw = 880, cy = 830, ch = 540;
  const m = { l: 130, r: 40, t: 40, b: 70 };
  const pw = cw - m.l - m.r;
  const ph = ch - m.t - m.b;
  const all = [...band.low, ...band.high, ...strategies.flat()];
  const lo = Math.min(...all) * 1.06;
  const hi = 0;
  const n = band.mid.length;
  const x = (i: number) => cx + m.l + (i / (n - 1)) * pw;
  const y = (v: number) => cy + m.t + ((hi - v) / (hi - lo)) * ph;
  const line = (vs: number[]) => vs.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area =
    line(band.high) +
    band.low
      .map((v, i) => [i, v] as const)
      .reverse()
      .map(([i, v]) => `L${x(i).toFixed(1)},${y(v).toFixed(1)}`)
      .join(" ") +
    " Z";
  const ticks: number[] = [];
  for (let t = 0; t >= lo; t -= 500) ticks.push(t);
  const grid = ticks
    .map(
      (t) => `<line x1="${cx + m.l}" x2="${cx + cw - m.r}" y1="${y(t)}" y2="${y(t)}" stroke="#e6e4de" stroke-width="2"/>
      <text x="${cx + m.l - 16}" y="${y(t)}" dy="0.35em" text-anchor="end" font-family="${font}" font-size="26" fill="#52514e">${t === 0 ? "0 €" : `${t.toLocaleString("it-IT")} €`}</text>`,
    )
    .join("");

  const rows = stats
    .map(
      (s, i) => `
    <text x="100" y="${1450 + i * 100}" font-family="${font}" font-weight="800" font-size="52" fill="#0b0b0b">${esc(s.value)}</text>
    <text x="310" y="${1450 + i * 100}" font-family="${font}" font-size="30" fill="#52514e">${esc(s.label)}</text>`,
    )
    .join("");

  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="16" stdDeviation="22" flood-color="#3d2f00" flood-opacity="0.16"/>
    </filter>
  </defs>
  <rect width="1080" height="1920" fill="#f9f9f7"/>
  <g transform="translate(540 330) rotate(-8) scale(2.4) translate(-32 -32)">${monkey}</g>
  <text x="540" y="470" text-anchor="middle" font-family="${font}" font-weight="700" font-size="28" fill="#52514e" letter-spacing="2">${esc(kicker.toUpperCase())}</text>
  <text x="540" y="570" text-anchor="middle" font-family="${font}" font-weight="800" font-size="82" fill="#0b0b0b">E se avessi giocato</text>
  <text x="540" y="665" text-anchor="middle" font-family="${font}" font-weight="800" font-size="82" fill="#0b0b0b">i tuoi numeri?</text>
  <text x="540" y="735" text-anchor="middle" font-family="${font}" font-size="32" fill="#52514e">${esc(intro[0])}</text>
  <text x="540" y="780" text-anchor="middle" font-family="${font}" font-size="32" fill="#52514e">${esc(intro[1])}</text>

  <g filter="url(#shadow)"><rect x="${cx}" y="${cy}" width="${cw}" height="${ch}" rx="36" fill="#ffffff"/></g>
  ${grid}
  <path d="${area}" fill="#f2c230" fill-opacity="0.45"/>
  <path d="${line(band.mid)}" fill="none" stroke="#b8860b" stroke-width="4" stroke-dasharray="12 8"/>
  ${strategies.map((s) => `<path d="${line(s)}" fill="none" stroke="#0b0b0b" stroke-width="3" stroke-opacity="0.75"/>`).join("")}
  <text x="${cx + m.l}" y="${cy + ch - 26}" font-family="${font}" font-size="26" fill="#52514e">${years[0]}</text>
  <text x="${cx + cw - m.r}" y="${cy + ch - 26}" text-anchor="end" font-family="${font}" font-size="26" fill="#52514e">${years[1]}</text>
  <rect x="${cx + 330}" y="${cy + ch - 50}" width="36" height="28" rx="6" fill="#f2c230" fill-opacity="0.45"/>
  <text x="${cx + 376}" y="${cy + ch - 26}" font-family="${font}" font-size="26" fill="#52514e">le scimmie</text>
  <line x1="${cx + 536}" x2="${cx + 576}" y1="${cy + ch - 36}" y2="${cy + ch - 36}" stroke="#0b0b0b" stroke-width="4"/>
  <text x="${cx + 588}" y="${cy + ch - 26}" font-family="${font}" font-size="26" fill="#52514e">le strategie</text>

  ${rows}

  <rect x="0" y="1600" width="1080" height="320" fill="#f2c230"/>
  <text x="540" y="1668" text-anchor="middle" font-family="${font}" font-size="32" fill="#3d2f00">Prova i tuoi sei numeri su</text>
  <text x="540" y="1726" text-anchor="middle" font-family="${font}" font-weight="800" font-size="46" fill="#3d2f00">lascimmiavince.federicodiluca.com</text>
</svg>`;
  return sharp(Buffer.from(svg)).png({ compressionLevel: 9, palette: true }).toBuffer();
}
