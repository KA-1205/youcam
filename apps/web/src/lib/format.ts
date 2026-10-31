/** Presentation helpers shared across surfaces. Pure and fixture-agnostic. */

export function formatMinor(minor: number, currency: string): string {
  const major = minor / 100;
  if (currency === "INR") {
    return `₹${major.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `${major.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

export function formatMoney(minor: number | null, currency: string): string {
  if (minor === null) return "Price unknown";
  return formatMinor(minor, currency);
}

export function formatStamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}` +
    ` ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`
  );
}

/**
 * Price/stock checks expire 15 minutes after the source refresh
 * (behavior contract §7). "stale" means the freshness window lapsed.
 */
export function freshness(checkedAt: string, expiresAt: string, now: string): "current" | "stale" {
  return new Date(now) < new Date(expiresAt) && new Date(now) >= new Date(checkedAt) ? "current" : "stale";
}
