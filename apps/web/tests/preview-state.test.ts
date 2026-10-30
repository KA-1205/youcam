import assert from "node:assert/strict";
import { test } from "node:test";
import { INITIAL_PREVIEW, capabilitySlots, previewReducer } from "../src/lib/preview-state";

test("capability change clears the job so categories compare independently", () => {
  const withJob = { ...INITIAL_PREVIEW, job: { jobId: "j", status: "SUCCEEDED", freshness: "CURRENT" as const, executionMode: "FIXTURE" as const, capability: "CLOTHES_V4", selections: [] } };
  const next = previewReducer(withJob, { type: "SET_CAPABILITY", capability: "MAKEUP" });
  assert.equal(next.capability, "MAKEUP");
  assert.equal(next.job, null);
});

test("selection toggles dedupe and clear the stale job", () => {
  let state = previewReducer(INITIAL_PREVIEW, { type: "TOGGLE_SELECTION", refId: "variant-top-1" });
  assert.deepEqual(state.selections, ["variant-top-1"]);
  state = previewReducer(state, { type: "TOGGLE_SELECTION", refId: "variant-top-1" });
  assert.deepEqual(state.selections, []);
});

test("superseded notice shows and a fresh job clears it", () => {
  let state = previewReducer(INITIAL_PREVIEW, { type: "SUPERSEDED" });
  assert.equal(state.supersededNotice, true);
  state = previewReducer(state, { type: "JOB", job: null });
  assert.equal(state.supersededNotice, false);
});

test("errors stop the busy flag", () => {
  const state = previewReducer({ ...INITIAL_PREVIEW, busy: true }, { type: "ERROR", message: "Failed" });
  assert.equal(state.error, "Failed");
  assert.equal(state.busy, false);
});

test("capability slots map to their product families", () => {
  assert.deepEqual(capabilitySlots("CLOTHES_V4"), ["TOP", "BOTTOM", "ONE_PIECE", "SHOES", "OUTER"]);
  assert.deepEqual(capabilitySlots("MAKEUP"), ["FOUNDATION", "LIP", "BLUSH"]);
  assert.deepEqual(capabilitySlots("EARRINGS"), ["EARRINGS"]);
  assert.deepEqual(capabilitySlots("HAIR_COLOR"), []);
  assert.ok(capabilitySlots("COMBINED").length > 10);
});
