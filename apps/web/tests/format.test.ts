import assert from "node:assert/strict";
import { test } from "node:test";
import { formatMoney, formatMinor, formatStamp, freshness } from "../src/lib/format";

test("money formats INR paise with the rupee sign", () => {
  assert.equal(formatMinor(200000, "INR"), "₹2,000.00");
  assert.equal(formatMinor(50, "INR"), "₹0.50");
});

test("formatMoney labels unknown prices instead of inventing one", () => {
  assert.equal(formatMoney(null, "INR"), "Price unknown");
  assert.equal(formatMoney(50000, "INR"), "₹500.00");
});

test("formatStamp renders a stable UTC stamp", () => {
  assert.equal(formatStamp("2026-10-30T00:00:00Z"), "2026-10-30 00:00 UTC");
});

test("freshness distinguishes current from expired price checks", () => {
  assert.equal(freshness("2026-10-30T00:00:00Z", "2026-10-30T00:15:00Z", "2026-10-30T00:05:00Z"), "current");
  assert.equal(freshness("2026-10-29T23:59:59Z", "2026-10-30T00:14:59Z", "2026-10-30T00:05:00Z"), "current");
  assert.equal(freshness("2026-10-29T23:59:59Z", "2026-10-30T00:15:00Z", "2026-10-30T00:20:00Z"), "stale");
});
