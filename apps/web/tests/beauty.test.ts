import assert from "node:assert/strict";
import { test } from "node:test";
import {
  BEAUTY_SLOTS,
  JEWELLERY_SLOTS,
  anchorMatchVerdict,
  addDiaryEntry,
  loadDiary,
  removeDiaryEntry,
  type DiaryEntry,
} from "../src/lib/beauty";

function fakeStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => map.set(k, v),
    removeItem: (k: string) => map.delete(k),
  };
}

test("beauty and jewellery slot families are separated", () => {
  assert.deepEqual(BEAUTY_SLOTS, ["FOUNDATION", "LIP", "BLUSH"]);
  assert.deepEqual(JEWELLERY_SLOTS, ["EARRINGS", "NECKLACE", "RING", "BRACELET", "WATCH"]);
});

test("anchor match never claims a shade match without evidence", () => {
  const verdict = anchorMatchVerdict({ crosswalkVerified: false, measuredEvidence: false });
  assert.equal(verdict.kind, "INSUFFICIENT");
  assert.match(verdict.message, /Insufficient matching evidence/i);
  assert.equal(verdict.shadeMatch, null);
});

test("anchor match requires verified crosswalk or measured evidence, not vibes", () => {
  assert.equal(anchorMatchVerdict({ crosswalkVerified: true, measuredEvidence: false }).kind, "MATCHED");
  assert.equal(anchorMatchVerdict({ crosswalkVerified: false, measuredEvidence: true }).kind, "MATCHED");
});

test("diary entries persist locally with subjective evidence labels", () => {
  const storage = fakeStorage();
  const added = addDiaryEntry(storage, { note: "The earrings read well in daylight." });
  assert.equal(added.kind, "SUBJECTIVE_OBSERVATION");
  const loaded = loadDiary(storage);
  assert.equal(loaded.length, 1);
  assert.match(loaded[0].note, /earrings/);
});

test("diary entries can be removed and tolerate corrupt storage", () => {
  const storage = fakeStorage();
  const entry = addDiaryEntry(storage, { note: "First wear." });
  removeDiaryEntry(storage, entry.id);
  assert.deepEqual(loadDiary(storage), []);
  const corrupt = fakeStorage({ "anchor-fit.wear-diary": "nope" });
  assert.deepEqual(loadDiary(corrupt), []);
});

test("diary entries keep an explicit catalogue-fact label when product-linked", () => {
  const storage = fakeStorage();
  const entry = addDiaryEntry(storage, { note: "Wore the demo top.", refId: "variant-top-1" });
  const loaded = loadDiary(storage);
  assert.deepEqual(loaded.map((e: DiaryEntry) => e.kind), ["CATALOG_FACT"]);
  assert.equal(entry.refId, "variant-top-1");
});
