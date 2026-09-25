/**
 * Colonna con l'estremo dati arrotondato (4px) e la base squadrata.
 * `base` è la y della linea di base, `end` la y dell'estremo: funziona anche verso il basso.
 */
export function columnPath(x: number, width: number, base: number, end: number, radius = 4): string {
  const h = Math.abs(end - base);
  if (h < 0.5) return "";
  const r = Math.min(radius, width / 2, h);
  const up = end < base;
  const s = up ? 1 : -1; // direzione dall'estremo verso la base
  return [
    `M${x},${base}`,
    `V${end + s * r}`,
    `Q${x},${end} ${x + r},${end}`,
    `H${x + width - r}`,
    `Q${x + width},${end} ${x + width},${end + s * r}`,
    `V${base}`,
    "Z",
  ].join(" ");
}

/** Tick "puliti" per un asse: passo 1/2/5 × 10^k. */
export function niceStep(span: number, target = 5): number {
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  return (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
}
