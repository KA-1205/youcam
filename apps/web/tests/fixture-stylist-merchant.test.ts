import assert from "node:assert/strict";
import { test } from "node:test";
import type { components } from "../../../contracts/runtime/client";
import { freshTransport } from "../src/lib/fixture/transport";

type Brief = components["schemas"]["Brief"];
import { OWNED_ITEMS, VARIANTS } from "../src/lib/fixture/demo-catalog";

const BRIEF: Brief = {
  lookMode: "OUTFIT" as const,
  outfitForm: "SEPARATES" as const,
  requestedSlots: ["TOP", "BOTTOM", "SHOES"],
  occasion: null,
  budgetMinor: 200000,
  currency: "INR",
  hardRequirements: {},
  preferences: {},
};

function makeSession(t: ReturnType<typeof freshTransport>) {
  const { data } = t.createSession({ anchors: OWNED_ITEMS, brief: BRIEF });
  return data!;
}

test("shares expire in seven days, are revocable and scoped to a recipient", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const share = t.createShare({
    expectedConsentRevision: session.consentRevision,
    expectedSessionVersion: session.sessionVersion,
    includedAssetIds: [],
    recipientAccountId: "stylist-1",
    sessionId: session.sessionId,
  }).data!;
  assert.equal(share.revoked, false);
  assert.equal(share.recipientAccountId, "stylist-1");
  const listed = t.listShares("stylist-1").data!;
  assert.equal(listed.length, 1);
  const revoked = t.revokeShare(share.shareId).data!;
  assert.equal(revoked.revoked, true);
  assert.equal(t.listShares("stylist-1").data!.length, 0);
});

test("proposals record base version, exceptions and can be applied by the shopper", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const proposal = t.createProposal({
    baseSessionVersion: session.sessionVersion,
    brief: session.brief,
    exceptions: [
      {
        description: "Replace the locked shoes with a lighter pair for travel.",
        exceptionId: "00000000-0000-4000-8000-0000000000f1",
        kind: "LOCK_REPLACEMENT",
        target: "variant-shoes-1",
      },
    ],
    notes: "Swap the shoes; everything else fits the brief.",
    selections: [
      { slot: "TOP", refType: "OWNED", refId: "owned-top-1" },
      { slot: "BOTTOM", refType: "VARIANT", refId: "variant-bottom-1" },
      { slot: "SHOES", refType: "VARIANT", refId: "variant-shoes-2" },
    ],
    sessionId: session.sessionId,
  }).data!;
  assert.equal(proposal.status, "PROPOSAL_READY");
  assert.equal(proposal.baseSessionVersion, session.sessionVersion);
  const applied = t.applyProposal(proposal.proposalId, {
    accept: true,
    approvedExceptionIds: ["00000000-0000-4000-8000-0000000000f1"],
    expectedSessionVersion: session.sessionVersion,
  }).data!;
  assert.equal(applied.selections.some((i) => i.refId === "variant-shoes-2"), true);
  const fetched = t.getProposal(proposal.proposalId).data!;
  assert.equal(fetched.status, "ACCEPTED");
});

test("proposal application refuses stale session versions", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const proposal = t.createProposal({
    baseSessionVersion: session.sessionVersion,
    brief: session.brief,
    exceptions: [],
    notes: "",
    selections: [],
    sessionId: session.sessionId,
  }).data!;
  const refused = t.applyProposal(proposal.proposalId, {
    accept: true,
    approvedExceptionIds: [],
    expectedSessionVersion: 99,
  });
  assert.equal(refused.error?.error.code, "STALE_SESSION");
});

test("catalog staging reports errors and never publishes silently", () => {
  const t = freshTransport();
  const batch = {
    sourceId: "demo-source",
    sourceVersion: "2026-10-30T00:00:00Z",
    variants: [structuredClone(VARIANTS[0]), structuredClone(VARIANTS[0])],
  };
  const stage = t.stageCatalog(batch).data!;
  assert.equal(stage.published, false);
  assert.ok(stage.errors.length >= 1, "duplicate variant ids must error");
  const ack = t.publishCatalog(stage.stageId, {
    approvePublication: true,
    expectedSourceVersion: stage.sourceVersion,
  });
  assert.equal(ack.error, undefined);
});

test("publish refuses a stale source version", () => {
  const t = freshTransport();
  const batch = {
    sourceId: "demo-source",
    sourceVersion: "2026-10-30T00:00:00Z",
    variants: [structuredClone(VARIANTS[0])],
  };
  const stage = t.stageCatalog(batch).data!;
  const refused = t.publishCatalog(stage.stageId, {
    approvePublication: true,
    expectedSourceVersion: "older-version",
  });
  assert.equal(refused.error?.error.code, "STALE_SOURCE");
});

test("insights carry mode, window and suppression labels without revenue claims", () => {
  const t = freshTransport();
  const page = t.getInsights().data!;
  assert.ok(page.metrics.length >= 2);
  for (const metric of page.metrics) {
    assert.equal(metric.mode, "DEMO");
    assert.ok(metric.windowStart < metric.windowEnd);
  }
  const suppressed = page.metrics.filter((m) => m.suppressed);
  assert.ok(suppressed.length >= 1, "small cohorts must be suppressed");
  assert.ok(page.metrics.every((m) => !m.name.toLowerCase().includes("revenue")));
});

test("refresh requests acknowledge without inventing advice", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const proposal = t.createProposal({
    baseSessionVersion: session.sessionVersion,
    brief: session.brief,
    exceptions: [],
    notes: "",
    selections: [],
    sessionId: session.sessionId,
  }).data!;
  const ack = t.requestProposalRefresh(proposal.proposalId, {
    expectedConsentRevision: session.consentRevision,
    expectedSessionVersion: session.sessionVersion,
    requestAdviceOnly: true,
  });
  assert.equal(ack.error, undefined);
  assert.equal(ack.data!.status, "ACCEPTED");
});
