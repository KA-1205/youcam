import assert from "node:assert/strict";
import { test } from "node:test";
import { OWNED_ITEMS, VARIANTS, findVariant } from "../src/lib/fixture/demo-catalog";

test("demo catalog fixture covers every styling slot", () => {
  const slots = new Set(VARIANTS.map((v) => v.slot));
  for (const slot of [
    "TOP", "BOTTOM", "ONE_PIECE", "SHOES", "OUTER", "EARRINGS", "NECKLACE",
    "RING", "BRACELET", "WATCH", "FOUNDATION", "LIP", "BLUSH",
  ] as const) {
    assert.ok(slots.has(slot), `missing slot ${slot}`);
  }
  assert.equal(VARIANTS.length, 30);
});

test("demo catalog fixture keeps the deliberate edge states", () => {
  const unknownPrice = findVariant("variant-top-3");
  assert.equal(unknownPrice?.priceMinor, null);
  const outOfStock = findVariant("variant-top-4");
  assert.equal(outOfStock?.stock, 0);
  const stale = findVariant("variant-top-5");
  assert.ok(stale && stale.checkedAt < stale.expiresAt);
  assert.notEqual(stale?.checkedAt, VARIANTS[0].checkedAt);
  for (const variant of VARIANTS) {
    assert.equal(variant.tenantId, "demo-anchor-fit");
    assert.equal(variant.isSynthetic, true);
    assert.ok(variant.sourceVersion);
    assert.ok(variant.checkedAt && variant.expiresAt);
  }
});

test("owned demo items map to owned item refs", () => {
  assert.deepEqual(OWNED_ITEMS, [{ slot: "TOP", refType: "OWNED", refId: "owned-top-1" }]);
});

test("findVariant misses unknown ids", () => {
  assert.equal(findVariant("variant-nonesuch"), undefined);
});
