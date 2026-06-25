// Formatting helpers that tolerate the honest "no data yet" case.
// Real recommendations carry null price/value until first-party tracking accrues,
// so every numeric render must degrade to an em dash rather than crash on .toFixed().

export function usd(n: number | null | undefined, digits = 0): string {
  return n == null ? "—" : `$${n.toFixed(digits)}`;
}

export function ratio(n: number | null | undefined, digits = 2): string {
  return n == null ? "—" : n.toFixed(digits);
}
