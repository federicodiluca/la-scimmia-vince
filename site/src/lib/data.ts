// Dati generati da `scimmia stats --out site/src/data/generated` (vedi README).
import drawsJson from "../data/generated/draws.json";
import frequencyJson from "../data/generated/frequency.json";
import honestyJson from "../data/generated/honesty.json";
import numbersJson from "../data/generated/numbers.json";
import summaryJson from "../data/generated/summary.json";

export interface Draw {
  id: string;
  date: string;
  n: number[];
  j: number;
  s: number | null;
  /** ritardo di ciascuno dei 6 numeri prima di questa estrazione */
  d: number[];
}

export interface NumberStats {
  number: number;
  count: number;
  rank: number;
  jolly: number;
  superstar: number;
  delay: { current: number; max: number; mean: number | null; last_seen: string | null };
  by_year: Record<string, number>;
  partners: { number: number; count: number }[];
}

export interface Summary {
  generated_at: string;
  draws: number;
  first_date: string;
  last_draw: Draw;
  jackpot: {
    draw_id: string;
    pool_total_eur: number | null;
    carryover_eur: number | null;
    last_six: { id: string; date: string; winners: number; amount_eur: number; draws_since: number } | null;
  } | null;
}

export interface Band {
  expected: number;
  low: number;
  high: number;
  confidence: number;
  outside: number;
}

export interface FakeDiscoveries {
  by: string;
  tests: number;
  alpha: number;
  expected_false_positives: number;
  naive_discoveries: number;
  survivors_family: number;
  survivors_after_correction: number;
  chi2_independence_p: number;
  groups: Record<string, number>;
  best_fake: {
    number: number;
    group: string | number;
    count: number;
    expected: number;
    ratio: number;
    p_value: number;
    p_family: number;
    p_adjusted: number;
  }[];
}

export interface FakeDiscoveriesAll {
  tests: number;
  naive_discoveries: number;
  expected_false_positives: number;
  survivors_family: number;
  survivors_after_correction: number;
  families: FakeDiscoveries[];
}

export interface DelayBucket {
  delay: string;
  opportunities: number;
  hits: number;
  hit_rate: number;
  ci_low: number;
  ci_high: number;
  expected: number;
}

export interface Uniformity {
  draws: number;
  expected_per_number: number;
  chi2: number;
  p_value: number;
  most: number;
  most_count: number;
  least: number;
  least_count: number;
}

export const summary = summaryJson as unknown as Summary;
export const draws = drawsJson as unknown as Draw[];
export const numbers = numbersJson as unknown as NumberStats[];
export const frequency = frequencyJson as unknown as {
  numbers: Record<string, number>;
  band: Band;
  jolly: Record<string, number>;
  superstar: Record<string, number>;
  by_year: Record<string, Record<string, number>>;
  by_weekday: Record<string, Record<string, number>>;
};
export const honesty = honestyJson as unknown as {
  uniformity: { numbers: Uniformity; jolly: Uniformity; superstar: Uniformity };
  fake_discoveries: FakeDiscoveriesAll;
  delay_fallacy: DelayBucket[];
};

export const P_HIT = 6 / 90;

export const years: number[] = [...new Set(draws.map((d) => Number(d.date.slice(0, 4))))].sort((a, b) => a - b);

export function drawsOfYear(year: number): Draw[] {
  return draws.filter((d) => d.date.startsWith(`${year}-`));
}

export function drawsPerYear(): Record<string, number> {
  const out: Record<string, number> = {};
  for (const d of draws) out[d.date.slice(0, 4)] = (out[d.date.slice(0, 4)] ?? 0) + 1;
  return out;
}

export function numberStats(n: number): NumberStats {
  const found = numbers.find((x) => x.number === n);
  if (!found) throw new Error(`numero ${n} non trovato`);
  return found;
}

// ---- simulatore "Se avessi giocato…" ----------------------------------------
import simulationJson from "../data/generated/simulation.json";

export interface StrategyResult {
  key: string;
  label: string;
  spent: number;
  won: number;
  returned: number;
  best_win: number;
  best_win_id: string | null;
  matches: Record<string, number>;
  unknown_jackpots: number;
  monkeys_better: number;
}

export interface Simulation {
  first: { id: string; date: string };
  last: { id: string; date: string };
  draws: number;
  players: number;
  spent: number;
  price_change: { id: string; date: string } | null;
  monkeys: {
    returned: Record<string, number>;
    best_returned: number;
    in_profit: number;
    final_sorted: number[];
  };
  strategies: StrategyResult[];
  curves: {
    dates: string[];
    monkeys: Record<"5" | "50" | "95", number[]>;
    strategies: Record<string, number[]>;
  };
}

export const simulation = simulationJson as unknown as Simulation;

// ---- dettaglio concorsi (quote e montepremi, dal 2009) -----------------------
import detailsJson from "../data/generated/details.json";

export interface DrawDetail {
  pool: number | null;
  carry: number | null;
  tiers: [game: string, category: string, winners: number, amount: number | null][];
}

export const details = detailsJson as unknown as Record<string, DrawDetail>;

const MONTHS_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

/** "2026-09-24" → "24-settembre": slug della pagina di un'estrazione dentro il suo anno. */
export function drawSlug(isoDate: string): string {
  const [, m, d] = isoDate.split("-");
  return `${Number(d)}-${MONTHS_IT[Number(m) - 1]}`;
}

export function drawPath(draw: Draw): string {
  return `estrazioni/${draw.date.slice(0, 4)}/${drawSlug(draw.date)}`;
}
