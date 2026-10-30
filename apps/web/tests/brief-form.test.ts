import assert from "node:assert/strict";
import { test } from "node:test";
import {
  INITIAL_FORM,
  anchorRef,
  buildBrief,
  buildSessionCreate,
  inferredOutfitForm,
  validateBriefForm,
  type BriefFormState,
} from "../src/lib/brief-form";

const VALID: BriefFormState = { ...INITIAL_FORM };

test("owned anchor maps to the demo owned item ref", () => {
  assert.deepEqual(anchorRef(VALID), { slot: "TOP", refType: "OWNED", refId: "owned-top-1" });
});

test("catalog anchor requires a chosen variant and maps its slot", () => {
  assert.equal(anchorRef({ ...VALID, anchorSource: "CATALOG", anchorVariantId: null }), null);
  assert.deepEqual(anchorRef({ ...VALID, anchorSource: "CATALOG", anchorVariantId: "variant-top-1" }), {
    slot: "TOP",
    refType: "VARIANT",
    refId: "variant-top-1",
  });
});

test("outfit form is inferred from the anchor, never from jewellery or beauty", () => {
  assert.equal(inferredOutfitForm({ slot: "TOP", refType: "OWNED", refId: "owned-top-1" }), "SEPARATES");
  assert.equal(inferredOutfitForm({ slot: "ONE_PIECE", refType: "VARIANT", refId: "v" }), "ONE_PIECE");
  assert.equal(inferredOutfitForm({ slot: "EARRINGS", refType: "VARIANT", refId: "v" }), null);
});

test("the form cannot submit without an anchor", () => {
  const problem = validateBriefForm({ ...VALID, anchorSource: "CATALOG", anchorVariantId: null });
  assert.equal(problem?.field, "anchor");
});

test("category set mode requires at least one category", () => {
  const problem = validateBriefForm({ ...VALID, lookMode: "CATEGORY_SET", requestedSlots: [] });
  assert.equal(problem?.field, "requestedSlots");
});

test("budget converts rupees to paise and accepts an empty budget", () => {
  assert.equal(buildBrief(VALID).budgetMinor, 200000);
  assert.equal(buildBrief({ ...VALID, budgetMajor: "" }).budgetMinor, null);
  assert.equal(buildBrief({ ...VALID, budgetMajor: "1999.5" }).budgetMinor, 199950);
});

test("a valid form builds a session create with the anchor and brief", () => {
  const result = buildSessionCreate(VALID);
  assert.ok("anchors" in result);
  if (!("anchors" in result)) return;
  assert.equal(result.anchors.length, 1);
  assert.equal(result.brief.lookMode, "OUTFIT");
  assert.equal(result.brief.outfitForm, "SEPARATES");
  assert.deepEqual(result.brief.requestedSlots, ["TOP", "BOTTOM", "SHOES"]);
});

test("an invalid form returns its validation error instead of a payload", () => {
  const result = buildSessionCreate({ ...VALID, anchorSource: "CATALOG", anchorVariantId: null });
  assert.ok("error" in result);
});
