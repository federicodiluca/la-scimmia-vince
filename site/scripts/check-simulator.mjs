// Verifica che il simulatore del browser (src/lib/simulator.ts) faccia gli stessi conti di quello
// Python: `scimmia stats` scrive i risultati di riferimento in simulator-check.json.
// Uso: npm test (dopo `scimmia stats --out site/src/data/generated`). Esce con 1 alla prima discrepanza.
import { readFileSync } from "node:fs";
import { simulate } from "../src/lib/simulator.ts";

const generated = new URL("../src/data/generated/", import.meta.url);
const game = JSON.parse(readFileSync(new URL("game.json", generated), "utf8"));
const cases = JSON.parse(readFileSync(new URL("simulator-check.json", generated), "utf8"));

const close = (a, b) => Math.abs(a - b) < 0.01;
const failures = [];
for (const ref of cases) {
  const r = simulate(game.draws, ref.picks);
  const hits = r.byTier.map((t) => t.hits);
  const checks = {
    spesa: [r.spent, ref.spent, close(r.spent, ref.spent)],
    vinto: [r.won, ref.won, close(r.won, ref.won)],
    "saldo finale": [r.balance.at(-1), ref.won - ref.spent, close(r.balance.at(-1), ref.won - ref.spent)],
    "saldo a metà": [r.balance[r.balance.length >> 1], ref.balance_mid, close(r.balance[r.balance.length >> 1], ref.balance_mid)],
    "senza quota": [r.unknown.length, ref.unknown, r.unknown.length === ref.unknown],
    "vincita migliore": [r.best?.amount ?? 0, ref.best, close(r.best?.amount ?? 0, ref.best)],
    "concorso migliore": [r.best?.id ?? null, ref.best_id, (r.best?.id ?? null) === ref.best_id],
    // il 2 si confronta solo in parte: prima del 2017 non era un premio e il JS non lo conta
    "punti 3/4/5/6": [
      [hits[1], hits[2], hits[3] + hits[4], hits[5]].join(","),
      [ref.matches["3"], ref.matches["4"], ref.matches["5"], ref.matches["6"]].join(","),
      hits[1] === ref.matches["3"] && hits[2] === ref.matches["4"] && hits[3] + hits[4] === ref.matches["5"] && hits[5] === ref.matches["6"],
    ],
  };
  for (const [what, [js, py, ok]] of Object.entries(checks)) {
    if (!ok) failures.push(`${ref.picks.join(" ")}: ${what} JS ${js} ≠ Python ${py}`);
  }
}

if (failures.length) {
  console.error(`Simulatore JS diverso da Python in ${failures.length} controlli:\n${failures.slice(0, 20).join("\n")}`);
  process.exit(1);
}
const unknown = cases.filter((c) => c.unknown).length;
console.log(`Simulatore JS = Python su ${cases.length} giocate (${unknown} con vincite senza quota).`);
