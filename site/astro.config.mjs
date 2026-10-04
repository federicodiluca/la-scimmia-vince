import { readFileSync } from "node:fs";
import sitemap from "@astrojs/sitemap";
import { defineConfig } from "astro/config";

// lastmod nella sitemap: le pagine delle estrazioni non cambiano più dopo il concorso (e l'archivio di un anno chiuso
// dopo la sua ultima estrazione); tutte le altre cambiano a ogni concorso, quindi prendono la data dell'ultimo.
const MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
const drawDates = JSON.parse(readFileSync(new URL("src/data/generated/draws.json", import.meta.url), "utf8")).map((d) => d.date);
const lastDate = drawDates.reduce((a, b) => (b > a ? b : a));
const lastOfYear = {};
for (const d of drawDates) if (d > (lastOfYear[d.slice(0, 4)] ?? "")) lastOfYear[d.slice(0, 4)] = d;

function lastmod(pathname) {
  const draw = pathname.match(/^\/estrazioni\/(\d{4})\/(\d+)-([a-z]+)\/$/);
  if (draw) {
    const month = String(MONTHS.indexOf(draw[3]) + 1).padStart(2, "0");
    return `${draw[1]}-${month}-${draw[2].padStart(2, "0")}`;
  }
  const year = pathname.match(/^\/estrazioni\/(\d{4})\/$/);
  if (year) return lastOfYear[year[1]] ?? lastDate;
  return lastDate;
}

export default defineConfig({
  site: "https://lascimmiavince.federicodiluca.com",
  base: "/",
  trailingSlash: "always",
  // la compressione mangia gli spazi tra testo ed elementi inline a capo ("sono<em>vere</em>")
  compressHTML: false,
  integrations: [
    sitemap({
      filter: (page) => !page.includes("/og/"),
      serialize: (item) => ({ ...item, lastmod: lastmod(new URL(item.url).pathname) }),
    }),
  ],
});
