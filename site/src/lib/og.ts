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
