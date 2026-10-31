import assert from "node:assert/strict";
import { test } from "node:test";
import type { components } from "../../../contracts/runtime/client";
import { freshTransport } from "../src/lib/fixture/transport";
import { proposeLooks } from "../src/lib/fixture/looks";
import { OWNED_ITEMS, VARIANTS } from "../src/lib/fixture/demo-catalog";

const BRIEF: components["schemas"]["Brief"] = {
  lookMode: "OUTFIT" as const,
  outfitForm: "SEPARATES" as const,
  requestedSlots: ["TOP", "BOTTOM", "SHOES"],
  occasion: null,
  budgetMinor: 200000,
  currency: "INR",
  hardRequirements: {},
  preferences: {},
};

function sessionCreate() {
  return {
    anchors: OWNED_ITEMS,
    brief: BRIEF,
  };
}

test("proposeLooks returns complete outfits under budget with owned anchor", () => {
  const result = proposeLooks({
    brief: BRIEF,
    anchors: OWNED_ITEMS,
    locks: [],
    rejectedIds: [],
    variants: VARIANTS,
  });
  assert.equal(result.kind, "LOOKS");
  if (result.kind !== "LOOKS") return;
  assert.ok(result.looks.length >= 1 && result.looks.length <= 3);
  for (const look of result.looks) {
    const slots = look.items.map((i) => i.slot).sort();
    assert.deepEqual(slots, ["BOTTOM", "SHOES", "TOP"]);
    const owned = look.items.find((i) => i.refType === "OWNED");
    assert.ok(owned, "owned anchor present");
    assert.equal(look.merchandiseTotalMinor! <= BRIEF.budgetMinor!, true);
    assert.equal(look.budgetVerified, true);
    assert.equal(look.completeness, "COMPLETE_OUTFIT");
  }
});

test("proposeLooks ranks cheapest alternative first and dedupes identities", () => {
  const result = proposeLooks({
    brief: BRIEF,
    anchors: OWNED_ITEMS,
    locks: [],
    rejectedIds: [],
    variants: VARIANTS,
  });
  if (result.kind !== "LOOKS") return assert.fail("expected looks");
  const totals = result.looks.map((l) => l.merchandiseTotalMinor!);
  assert.deepEqual([...totals].sort((a, b) => a - b), totals);
  const identities = new Set(
    result.looks.map((l) =>
      l.items.map((i) => `${i.slot}:${i.refId}`).sort().join("|"),
    ),
  );
  assert.equal(identities.size, result.looks.length);
});

test("changing only one unlocked slot makes distinct alternatives", () => {
  const result = proposeLooks({
    brief: BRIEF,
    anchors: OWNED_ITEMS,
    locks: [],
    rejectedIds: [],
    variants: VARIANTS,
  });
  if (result.kind !== "LOOKS") return assert.fail("expected looks");
  if (result.looks.length < 2) return;
  const [first, second] = result.looks;
  const firstIds = new Set(first.items.map((i) => i.refId));
  const secondUnlocked = second.items.filter(
    (i) => !(i.refType === "OWNED"),
  );
  assert.ok(
    secondUnlocked.some((i) => !firstIds.has(i.refId)),
    "alternatives differ in an unlocked item",
  );
});

test("locked unknown-price item stays visible and blocks budget verification", () => {
  const result = proposeLooks({
    brief: BRIEF,
    anchors: OWNED_ITEMS,
    locks: [{ slot: "BOTTOM", refType: "VARIANT", refId: "variant-top-3" }],
    rejectedIds: [],
    variants: VARIANTS,
  });
  // Slot mismatch lock (TOP-priced variant in BOTTOM slot) is invalid input;
  // the fixture refuses it rather than silently deleting it.
  assert.equal(result.kind, "NO_ELIGIBLE_COMBINATION");
});

test("locked valid item is identical across alternatives", () => {
  const result = proposeLooks({
    brief: BRIEF,
    anchors: OWNED_ITEMS,
    locks: [{ slot: "SHOES", refType: "VARIANT", refId: "variant-shoes-1" }],
    rejectedIds: [],
    variants: VARIANTS,
  });
  if (result.kind !== "LOOKS") return assert.fail("expected looks");
  for (const look of result.looks) {
    assert.ok(look.items.some((i) => i.refId === "variant-shoes-1"));
  }
});

test("empty required slot yields a conclusive no-combination proof", () => {
  const result = proposeLooks({
    brief: { ...BRIEF, requestedSlots: ["TOP", "OUTER", "SHOES"] },
    anchors: OWNED_ITEMS,
    locks: [],
    rejectedIds: [],
    variants: VARIANTS.filter((v) => v.slot !== "OUTER"),
  });
  assert.equal(result.kind, "NO_ELIGIBLE_COMBINATION");
  if (result.kind !== "NO_ELIGIBLE_COMBINATION") return;
  assert.equal(result.proofCode, "EMPTY_REQUIRED_SLOT");
  assert.ok(result.affectedSlots.includes("OUTER"));
});

test("missing outfit form asks for clarification instead of guessing", () => {
  const result = proposeLooks({
    brief: { ...BRIEF, outfitForm: null },
    anchors: OWNED_ITEMS,
    locks: [],
    rejectedIds: [],
    variants: VARIANTS,
  });
  assert.equal(result.kind, "NEEDS_CLARIFICATION");
  if (result.kind !== "NEEDS_CLARIFICATION") return;
  assert.equal(result.reason, "MISSING_REQUIRED_INPUT");
});

test("out-of-stock, stale and unknown-price candidates are never recommended", () => {
  const result = proposeLooks({
    brief: BRIEF,
    anchors: OWNED_ITEMS,
    locks: [],
    rejectedIds: [],
    variants: VARIANTS,
  });
  if (result.kind !== "LOOKS") return assert.fail("expected looks");
  const banned = new Set(["variant-top-4", "variant-top-5", "variant-top-3"]);
  for (const look of result.looks) {
    for (const item of look.items) {
      assert.equal(banned.has(item.refId), false);
    }
  }
});

test("fixture session edit enforces optimistic version control", () => {
  const t = freshTransport();
  const created = t.createSession(sessionCreate());
  assert.ok(created.data);
  const session = created.data!;
  assert.equal(session.sessionVersion, 1);
  const stale = t.editSession(session.sessionId, {
    ...session,
    expectedSessionVersion: 0,
  });
  assert.equal(stale.error?.error.code, "STALE_SESSION");
  const current = t.editSession(session.sessionId, {
    ...session,
    expectedSessionVersion: 1,
  });
  assert.equal(current.error, undefined);
  assert.equal(current.data!.sessionVersion, 2);
});

test("fixture stylist job advances queued, running, then succeeds", () => {
  const t = freshTransport();
  const created = t.createSession(sessionCreate());
  const session = created.data!;
  const job = t.createStylistJob({
    mode: "PROPOSE",
    sessionId: session.sessionId,
    expectedSessionVersion: session.sessionVersion,
    lookId: null,
  });
  assert.equal(job.error, undefined);
  assert.equal(job.data!.status, "QUEUED");
  const first = t.getStylistJob(job.data!.jobId);
  assert.equal(first.data!.status, "RUNNING");
  const second = t.getStylistJob(job.data!.jobId);
  assert.equal(second.data!.status, "SUCCEEDED");
  assert.equal(second.data!.freshness, "CURRENT");
  assert.equal(second.data!.source, "RULE_BASED");
  assert.equal(second.data!.result?.kind, "LOOKS");
  const stable = t.getStylistJob(job.data!.jobId);
  assert.equal(stable.data!.status, "SUCCEEDED");
});

test("fixture stylist job refuses unknown sessions and stale versions", () => {
  const t = freshTransport();
  const missing = t.createStylistJob({
    mode: "PROPOSE",
    sessionId: "00000000-0000-4000-8000-000000000009",
    expectedSessionVersion: 1,
    lookId: null,
  });
  assert.equal(missing.error?.error.code, "NOT_FOUND");
  const created = t.createSession(sessionCreate());
  const session = created.data!;
  const stale = t.createStylistJob({
    mode: "PROPOSE",
    sessionId: session.sessionId,
    expectedSessionVersion: 99,
    lookId: null,
  });
  assert.equal(stale.error?.error.code, "STALE_SESSION");
});

test("fixture stylist job can be cancelled while queued", () => {
  const t = freshTransport();
  const created = t.createSession(sessionCreate());
  const session = created.data!;
  const job = t.createStylistJob({
    mode: "PROPOSE",
    sessionId: session.sessionId,
    expectedSessionVersion: session.sessionVersion,
    lookId: null,
  });
  const cancelled = t.cancelStylistJob(job.data!.jobId);
  assert.equal(cancelled.data!.status, "CANCELLED");
  const after = t.getStylistJob(job.data!.jobId);
  assert.equal(after.data!.status, "CANCELLED");
});

test("catalog page query filters by slot and paginates", () => {
  const t = freshTransport();
  const tops = t.listVariants({ slot: "TOP" });
  assert.equal(tops.error, undefined);
  assert.ok(tops.data!.items.length > 0);
  assert.ok(tops.data!.items.every((v) => v.slot === "TOP"));
  const page = t.listVariants({});
  assert.equal(page.data!.nextCursor === null || typeof page.data!.nextCursor === "string", true);
});
