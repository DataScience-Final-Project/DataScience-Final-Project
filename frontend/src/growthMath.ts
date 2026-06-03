/** Parse filter value e.g. "6+" → 6 */
export function parseYearsForward(yearsForward: string | number): number {
  return Math.max(1, Number(String(yearsForward).replace("+", "")) || 1);
}

/** DB may store 0.08 (rate) or 8 (percent) — always return decimal rate for compounding. */
export function toDecimalGrowthRate(avgGrowth: number): number {
  if (!Number.isFinite(avgGrowth)) return 0;
  return Math.abs(avgGrowth) > 1 ? avgGrowth / 100 : avgGrowth;
}

/** Total projected % over `years` from per-period decimal rate. */
export function projectedGrowthPercent(rate: number, years: number): number {
  const y = parseYearsForward(years);
  const r = toDecimalGrowthRate(rate);
  return Number(((Math.pow(1 + r, y) - 1) * 100).toFixed(3));
}

/** CAGR % from total projected % — stable scale for map colors across year horizons. */
export function annualizedGrowthPercent(totalPercent: number, years: number): number {
  const y = parseYearsForward(years);
  const total = totalPercent / 100;
  if (total <= -1) return 0;
  return Number(((Math.pow(1 + total, 1 / y) - 1) * 100).toFixed(3));
}
