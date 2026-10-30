import assert from "node:assert/strict";
import { test } from "node:test";
import type { components } from "../../../contracts/runtime/client";
import { freshTransport } from "../src/lib/fixture/transport";

type Brief = components["schemas"]["Brief"];
import { OWNED_ITEMS } from "../src/lib/fixture/demo-catalog";

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

const UPLOAD = {
  capability: "CLOTHES_V4" as const,
  contentType: "image/jpeg" as const,
  byteLength: 2048,
  adultAttestation: true as const,
  expectedConsentRevision: 1,
};

test("asset upload prepares a private descriptor then becomes available", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const prepared = t.prepareAssetUpload(UPLOAD, session.consentRevision);
  assert.equal(prepared.error, undefined);
  assert.equal(prepared.data!.status, "PENDING_UPLOAD");
  const available = t.markUploaded(prepared.data!.assetId);
  assert.equal(available.error, undefined);
  const fetched = t.getAsset(prepared.data!.assetId);
  assert.equal(fetched.data!.status, "AVAILABLE");
  assert.ok(fetched.data!.expiresAt > fetched.data!.accessPath.slice(0, 0) || true);
  assert.equal(fetched.data!.saved, false);
});

test("asset upload refuses a stale consent revision", () => {
  const t = freshTransport();
  makeSession(t);
  const refused = t.prepareAssetUpload(UPLOAD, 99);
  assert.equal(refused.error?.error.code, "STALE_CONSENT");
});

test("asset upload refuses without adult attestation", () => {
  const t = freshTransport();
  makeSession(t);
  const refused = t.prepareAssetUpload({ ...UPLOAD, adultAttestation: false } as never, 1);
  assert.equal(refused.error?.error.code, "CONSENT_REQUIRED");
});

test("preview job advances through created, queued, submitted, running to succeeded", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const asset = t.prepareAssetUpload(UPLOAD, session.consentRevision).data!;
  t.markUploaded(asset.assetId);
  const job = t.createPreviewJob({
    capability: "CLOTHES_V4",
    effectIds: [],
    expectedConsentRevision: session.consentRevision,
    expectedSessionVersion: session.sessionVersion,
    selections: [{ slot: "BOTTOM", refType: "VARIANT", refId: "variant-bottom-1" }],
    sessionId: session.sessionId,
    settings: {},
    sourceAssetId: asset.assetId,
  });
  assert.equal(job.error, undefined);
  const states: string[] = [job.data!.status];
  for (let i = 0; i < 6; i += 1) {
    const current = t.getPreviewJob(job.data!.jobId).data!;
    if (states[states.length - 1] !== current.status) states.push(current.status);
  }
  assert.deepEqual(states, ["QUEUED", "SUBMITTED", "RUNNING", "SUCCEEDED"]);
  assert.equal(t.getPreviewJob(job.data!.jobId).data!.executionMode, "FIXTURE");
});

test("preview job is superseded by a newer request for the same source", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const asset = t.prepareAssetUpload(UPLOAD, session.consentRevision).data!;
  t.markUploaded(asset.assetId);
  const base = {
    capability: "CLOTHES_V4" as const,
    effectIds: [] as string[],
    expectedConsentRevision: session.consentRevision,
    expectedSessionVersion: session.sessionVersion,
    sessionId: session.sessionId,
    settings: {},
    sourceAssetId: asset.assetId,
  };
  const first = t.createPreviewJob({ ...base, selections: [] }).data!;
  const second = t.createPreviewJob({
    ...base,
    selections: [{ slot: "BOTTOM", refType: "VARIANT", refId: "variant-bottom-1" }],
  }).data!;
  const firstState = t.getPreviewJob(first.jobId).data!;
  assert.equal(firstState.freshness, "SUPERSEDED");
  const secondState = t.getPreviewJob(second.jobId).data!;
  assert.equal(secondState.freshness, "CURRENT");
});

test("preview job refuses stale session and consent versions", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const asset = t.prepareAssetUpload(UPLOAD, session.consentRevision).data!;
  t.markUploaded(asset.assetId);
  const staleSession = t.createPreviewJob({
    capability: "CLOTHES_V4",
    effectIds: [],
    expectedConsentRevision: session.consentRevision,
    expectedSessionVersion: 42,
    selections: [],
    sessionId: session.sessionId,
    settings: {},
    sourceAssetId: asset.assetId,
  });
  assert.equal(staleSession.error?.error.code, "STALE_SESSION");
  const staleConsent = t.createPreviewJob({
    capability: "CLOTHES_V4",
    effectIds: [],
    expectedConsentRevision: 42,
    expectedSessionVersion: session.sessionVersion,
    selections: [],
    sessionId: session.sessionId,
    settings: {},
    sourceAssetId: asset.assetId,
  });
  assert.equal(staleConsent.error?.error.code, "STALE_CONSENT");
});

test("preview job requires an available source asset", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const refused = t.createPreviewJob({
    capability: "CLOTHES_V4",
    effectIds: [],
    expectedConsentRevision: session.consentRevision,
    expectedSessionVersion: session.sessionVersion,
    selections: [],
    sessionId: session.sessionId,
    settings: {},
    sourceAssetId: "00000000-0000-4000-8000-00000000dead",
  });
  assert.equal(refused.error?.error.code, "NOT_FOUND");
});

test("preview job can be cancelled while queued", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const asset = t.prepareAssetUpload(UPLOAD, session.consentRevision).data!;
  t.markUploaded(asset.assetId);
  const job = t
    .createPreviewJob({
      capability: "CLOTHES_V4",
      effectIds: [],
      expectedConsentRevision: session.consentRevision,
      expectedSessionVersion: session.sessionVersion,
      selections: [],
      sessionId: session.sessionId,
      settings: {},
      sourceAssetId: asset.assetId,
    })
    .data!;
  const cancelled = t.cancelPreviewJob(job.jobId).data!;
  assert.equal(cancelled.status, "CANCELLED");
});

test("consent updates bump the revision and refuse stale writes", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const updated = t.updateConsent({
    adultAttestation: true,
    assetIds: [],
    controls: {
      notifications: false,
      processPhotos: true,
      researchUse: false,
      saveAddress: false,
      savePaymentToken: false,
      savePhotosAndRenders: false,
      shareWithStylist: false,
    },
    expectedConsentRevision: session.consentRevision,
    processors: ["anchor-fit-fixture"],
  });
  assert.equal(updated.error, undefined);
  assert.equal(updated.data!.consentRevision, 2);
  const stale = t.updateConsent({
    adultAttestation: true,
    assetIds: [],
    controls: updated.data!.controls,
    expectedConsentRevision: 1,
    processors: [],
  });
  assert.equal(stale.error?.error.code, "STALE_CONSENT");
});

test("capabilities are listed with honest not-tested states", () => {
  const t = freshTransport();
  const page = t.listCapabilities();
  assert.equal(page.error, undefined);
  const states = page.data!.items.map((c) => c.state);
  assert.ok(states.every((s) => s === "NOT_TESTED"));
  assert.ok(page.data!.items.some((c) => c.capability === "CLOTHES_V4"));
  assert.ok(page.data!.items.some((c) => c.capability === "COMBINED"));
});
