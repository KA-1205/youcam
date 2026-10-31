import assert from "node:assert/strict";
import { test } from "node:test";
import { toggleSaved, loadShortlist, saveShortlist } from "../src/lib/shortlist";

function fakeStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => map.set(k, v),
    removeItem: (k: string) => map.delete(k),
  };
}

test("shortlist toggles product saves without duplicates", () => {
  const ids = ["variant-bottom-1"];
  const after = toggleSaved(ids, "variant-shoes-1");
  assert.deepEqual(after, ["variant-bottom-1", "variant-shoes-1"]);
  const again = toggleSaved(after, "variant-shoes-1");
  assert.deepEqual(again, ["variant-bottom-1"]);
});

test("shortlist persists product-only saves with no photo consent involved", () => {
  const storage = fakeStorage();
  saveShortlist(storage, ["variant-top-1", "variant-lip-1"]);
  const loaded = loadShortlist(storage);
  assert.deepEqual(loaded, ["variant-top-1", "variant-lip-1"]);
});

test("shortlist tolerates corrupt storage instead of crashing", () => {
  const storage = fakeStorage({ "anchor-fit.shortlist": "{not json" });
  assert.deepEqual(loadShortlist(storage), []);
});

test("empty storage yields an empty shortlist", () => {
  assert.deepEqual(loadShortlist(fakeStorage()), []);
});
