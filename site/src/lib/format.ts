// useGrouping "always": in italiano Intl non separa le migliaia a 4 cifre ("2044" accanto a "51.419")
const intFmt = new Intl.NumberFormat("it-IT", { useGrouping: "always" });
const pctFmt = new Intl.NumberFormat("it-IT", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const eurFmt = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0, useGrouping: "always" });
const eurCentsFmt = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", useGrouping: "always" });
const eurCompact = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 });
const dateFmt = new Intl.DateTimeFormat("it-IT", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const dayFmt = new Intl.DateTimeFormat("it-IT", { weekday: "long", timeZone: "UTC" });

export const int = (n: number) => intFmt.format(n);
export const dec = (n: number, digits = 1) =>
  new Intl.NumberFormat("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: "always" }).format(n);
export const pct = (n: number) => pctFmt.format(n);
export const eur = (n: number) => eurFmt.format(n);
/** importi esatti, es. le quote: 7.858,24 € */
export const eurCents = (n: number) => eurCentsFmt.format(n);
export const eurShort = (n: number) => eurCompact.format(n);
export const date = (iso: string) => dateFmt.format(new Date(`${iso}T00:00:00Z`));
export const weekday = (iso: string) => dayFmt.format(new Date(`${iso}T00:00:00Z`));

// Articoli davanti ai numeri: "l'8", "l'11", "l'85" ma "il 17", "il 90".
const elides = (n: number) => n === 1 || n === 8 || n === 11 || n === 18 || (n >= 80 && n <= 89);
export const il = (n: number) => (elides(n) ? `l'${n}` : `il ${n}`);
export const Il = (n: number) => (elides(n) ? `L'${n}` : `Il ${n}`);
export const del = (n: number) => (elides(n) ? `dell'${n}` : `del ${n}`);
export const al = (n: number) => (elides(n) ? `all'${n}` : `al ${n}`);

/** Link interno che rispetta il `base` di GitHub Pages. */
export function url(path = ""): string {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, "/");
  const clean = path.replace(/^\//, "");
  return clean ? `${base}${clean}`.replace(/\/?$/, clean.includes(".") || clean.includes("#") ? "" : "/") : base;
}

const MONTHS_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

/** "2026-09-24" → "24-settembre": slug della pagina di un'estrazione dentro il suo anno. */
export function drawSlug(isoDate: string): string {
  const [, m, d] = isoDate.split("-");
  return `${Number(d)}-${MONTHS_IT[Number(m) - 1]}`;
}

export function drawPath(draw: { date: string }): string {
  return `estrazioni/${draw.date.slice(0, 4)}/${drawSlug(draw.date)}`;
}
