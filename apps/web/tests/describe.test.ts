import assert from "node:assert/strict";
import { test } from "node:test";
import { describeItem } from "../src/lib/describe";

test("owned refs render as zero-spend owned items", () => {
  const view = describeItem({ slot: "TOP", refType: "OWNED", refId: "owned-top-1" });
  assert.equal(view.owned, true);
  assert.equal(view.priceMinor, 0);
  assert.match(view.title, /your/i);
});

test("variant refs render brand, price and stock from the fixture catalog", () => {
  const view = describeItem({ slot: "BOTTOM", refType: "VARIANT", refId: "variant-bottom-1" });
  assert.equal(view.owned, false);
  assert.equal(view.brand, "Anchor Demo");
  assert.equal(view.priceMinor, 60000);
  assert.equal(view.stock, 10);
  assert.equal(view.stale, false);
});

test("stale stock flags as stale without hiding the item", () => {
  const view = describeItem({ slot: "TOP", refType: "VARIANT", refId: "variant-top-5" });
  assert.equal(view.stale, true);
  assert.equal(view.priceMinor, 70000);
});

test("unknown refs keep their id rather than inventing facts", () => {
  const view = describeItem({ slot: "TOP", refType: "VARIANT", refId: "variant-nonesuch" });
  assert.equal(view.title, "variant-nonesuch");
  assert.equal(view.brand, "Unknown");
  assert.equal(view.priceMinor, null);
});
