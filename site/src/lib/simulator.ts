// Motore di "Se avessi giocato…" nel browser: stesse regole di `scimmia.simulate` (Python),
// una colonna a concorso con le quote reali. Nessuna dipendenza dai dati: li riceve come argomento.

/** [id, data, sestina, jolly, prezzo, quote 2/3/4/5/5+1/6 (-1 = categoria senza vincitori quel giorno)] */
export type Row = [id: string, date: string, numbers: number[], jolly: number, price: number, prizes: number[]];

export const TIERS = ["2", "3", "4", "5", "5+1", "6"] as const;
const FIVE_PLUS_ONE = 4;

/** Categoria centrata (indice in TIERS) o -1. */
export function tierOf(picks: readonly number[], numbers: readonly number[], jolly: number): number {
  let matched = 0;
  for (const p of picks) if (numbers.includes(p)) matched += 1;
  if (matched === 6) return 5;
  if (matched === 5 && picks.includes(jolly)) return FIVE_PLUS_ONE;
  return matched >= 2 ? matched - 2 : -1;
}

export interface Win {
  id: string;
  date: string;
  tier: number;
  /** null: nessuno l'ha centrata quel giorno, quindi non esiste una quota */
  amount: number | null;
}

export interface Outcome {
  picks: number[];
  spent: number;
  won: number;
  net: number;
  /** per categoria: volte centrate, somma incassata, volte senza quota */
  byTier: { hits: number; amount: number; unknown: number }[];
  best: Win | null;
  unknown: Win[];
  /** saldo cumulato dopo ogni concorso */
  balance: number[];
}

export function simulate(rows: readonly Row[], picks: readonly number[]): Outcome {
  let spent = 0;
  let won = 0;
  let best: Win | null = null;
  const unknown: Win[] = [];
  const byTier = TIERS.map(() => ({ hits: 0, amount: 0, unknown: 0 }));
  const balance: number[] = new Array(rows.length);
  for (let i = 0; i < rows.length; i++) {
    const [id, date, numbers, jolly, price, prizes] = rows[i]!;
    spent += price;
    const tier = tierOf(picks, numbers, jolly);
    const amount = tier >= 0 ? prizes[tier]! : 0;
    // quota 0: la categoria non esisteva ancora (il 2 prima del 2017), non è una vincita
    if (amount < 0) {
      byTier[tier]!.hits += 1;
      byTier[tier]!.unknown += 1;
      unknown.push({ id, date, tier, amount: null });
    } else if (amount > 0) {
      won += amount;
      byTier[tier]!.hits += 1;
      byTier[tier]!.amount += amount;
      if (!best || amount > best.amount!) best = { id, date, tier, amount };
    }
    balance[i] = won - spent;
  }
  return { picks: [...picks], spent, won, net: won - spent, byTier, best, unknown, balance };
}

/** Quota mediana di una categoria nei concorsi in cui è stata pagata: "quanto vale di solito". */
export function typicalPrize(rows: readonly Row[], tier: number): number {
  const paid = rows
    .map((r) => r[5][tier]!)
    .filter((v) => v > 0)
    .sort((a, b) => a - b);
  if (!paid.length) return 0;
  const mid = paid.length >> 1;
  return paid.length % 2 ? paid[mid]! : (paid[mid - 1]! + paid[mid]!) / 2;
}

/**
 * Numeri dall'indirizzo: `?n=3-17-22-45-60-88` (link condiviso) oppure `?n=3&n=17…` (form della home).
 * Tiene i numeri validi, senza doppioni, nell'ordine in cui arrivano; `invalid` segnala se ne ha scartati.
 */
export function parsePicks(search: string): { picks: number[]; invalid: boolean } {
  const raw = new URLSearchParams(search)
    .getAll("n")
    .flatMap((v) => v.split(/[\s,.;·-]+/))
    .filter(Boolean);
  const picks: number[] = [];
  for (const v of raw) {
    const n = Number(v);
    if (Number.isInteger(n) && n >= 1 && n <= 90 && !picks.includes(n) && picks.length < 6) picks.push(n);
  }
  return { picks, invalid: raw.length > 0 && (picks.length !== raw.length || picks.length !== 6) };
}
