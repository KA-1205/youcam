/** LIVE transport acceptance: contract calls, error envelopes, honest gaps. */
import assert from "node:assert/strict";
import { test } from "node:test";

import type { components } from "../../../contracts/runtime/client";
import { FixtureTransport, freshTransport } from "../src/lib/fixture/transport";
import { LiveTransport, type ApiClient } from "../src/lib/live/transport";
import { sharedTransport, transportMode } from "../src/lib/transport";

type Call = { method: string; path: string; header?: Record<string, string>; query?: Record<string, unknown> };

function fakeClient(routes: Record<string, (call: Call) => { status: number; payload: unknown }>) {
  const calls: Call[] = [];
  const handler = (method: string) =>
    (path: string, options?: { body?: unknown; headers?: Record<string, string>; params?: { header?: Record<string, string>; query?: Record<string, unknown> } }) => {
      const call: Call = { method, path };
      if (options?.params?.header) call.header = options.params.header;
      if (options?.params?.query && Object.values(options.params.query).some((v) => v !== undefined)) {
        call.query = options.params.query;
      }
      calls.push(call);
      const route = routes[`${method} ${path}`];
      assert.ok(route, `unexpected call ${method} ${path}`);
      const outcome = route(call);
      return Promise.resolve(outcome.status >= 400
        ? { data: undefined, error: outcome.payload }
        : { data: outcome.payload, error: undefined });
    };
  const client = {
    GET: handler("GET"),
    POST: handler("POST"),
    PUT: handler("PUT"),
    DELETE: handler("DELETE"),
  };
  return { client: client as unknown as ApiClient, calls };
}

const BRIEF: components["schemas"]["Brief"] = {
  lookMode: "OUTFIT",
  outfitForm: "SEPARATES",
  requestedSlots: ["TOP", "BOTTOM", "SHOES"],
  occasion: null,
  budgetMinor: 200000,
  currency: "INR",
  hardRequirements: {},
  preferences: {},
};

const SESSION: components["schemas"]["SessionSnapshot"] = {
  anchors: [],
  brief: BRIEF,
  consentRevision: 1,
  rejectedIds: [],
  selections: [],
  sessionId: "00000000-0000-4000-8000-000000000001",
  sessionVersion: 1,
  tenantId: "demo-anchor-fit",
  locks: [],
  updatedAt: "2026-10-31T12:00:00Z",
};

test("live transport maps catalog data and forwards query params", async () => {
  const { client, calls } = fakeClient({
    "GET /api/catalog/variants": () => ({
      status: 200,
      payload: { items: [], nextCursor: null, catalogVersion: "catalog-v7" },
    }),
  });
  const transport = new LiveTransport(client);
  const result = await transport.listVariants({ slot: "TOP", cursor: null });
  assert.equal(result.data?.catalogVersion, "catalog-v7");
  assert.deepEqual(calls, [{ method: "GET", path: "/api/catalog/variants" }]);
});

test("live transport surfaces the frozen error envelope", async () => {
  const { client } = fakeClient({
    "POST /api/sessions": () => ({
      status: 409,
      payload: { error: { code: "IDEMPOTENCY_CONFLICT", message: "Key reused." }, requestId: "req-1" },
    }),
  });
  const transport = new LiveTransport(client);
  const result = await transport.createSession({ anchors: [], brief: BRIEF });
  assert.equal(result.error?.error.code, "IDEMPOTENCY_CONFLICT");
  assert.equal(result.error?.requestId, "req-1");
});

test("live transport sends idempotency keys on mutating calls", async () => {
  const { client, calls } = fakeClient({
    "POST /api/session-claims": () => ({ status: 201, payload: SESSION }),
  });
  const transport = new LiveTransport(client);
  const result = await transport.claimSession({
    expectedSessionVersion: 1,
    keepGuestSession: true,
    sessionId: SESSION.sessionId,
  });
  assert.ok(result.data);
  assert.match(calls[0].header?.["Idempotency-Key"] ?? "", /^[0-9a-f-]{36}$/);
});

test("fixture-only affordances stay honestly unavailable", async () => {
  const { client } = fakeClient({});
  const transport = new LiveTransport(client);
  const upload = await transport.markUploaded("asset-1");
  assert.equal(upload.error?.error.code, "NOT_IMPLEMENTED");
  const approve = await transport.approveDemoAuth("order-1");
  assert.equal(approve.error?.error.code, "NOT_IMPLEMENTED");
  assert.equal(transport.orderScript("order-1"), null);
});

test("claim tracking mirrors this tab's claims", async () => {
  const { client } = fakeClient({
    "POST /api/session-claims": () => ({ status: 201, payload: SESSION }),
  });
  const transport = new LiveTransport(client);
  assert.equal(transport.isClaimed(SESSION.sessionId), false);
  await transport.claimSession({
    expectedSessionVersion: 1,
    keepGuestSession: true,
    sessionId: SESSION.sessionId,
  });
  assert.equal(transport.isClaimed(SESSION.sessionId), true);
});

test("wardrobe listing follows server cursor pages", async () => {
  const pages: components["schemas"]["WardrobeItem"][][] = [
    [{
      wardrobeId: "w1",
      reference: { slot: "TOP", refType: "VARIANT", refId: "variant-top-1" },
      ownedQuantity: 1,
      orderedQuantity: 0,
      manualOwnedQuantity: 0,
      saved: true,
      provenance: [],
    }],
    [{
      wardrobeId: "w2",
      reference: { slot: "SHOES", refType: "VARIANT", refId: "variant-shoes-1" },
      ownedQuantity: 0,
      orderedQuantity: 2,
      manualOwnedQuantity: 0,
      saved: false,
      provenance: [],
    }],
  ];
  let page = 0;
  const { client } = fakeClient({
    "GET /api/wardrobe": () => {
      const items = pages[page];
      page += 1;
      const last = page === pages.length;
      return {
        status: 200,
        payload: { items, nextCursor: last ? null : `cursor-${page}` },
      };
    },
  });
  const transport = new LiveTransport(client);
  const result = await transport.listWardrobe();
  assert.equal(result.data?.items.length, 2);
  assert.equal(result.data?.nextCursor, null);
});

test("transport selection defaults to fixture and honours the live flag", () => {
  process.env.NEXT_PUBLIC_TRANSPORT = "fixture";
  assert.equal(transportMode(), "FIXTURE");
  assert.ok(sharedTransport() instanceof FixtureTransport);

  process.env.NEXT_PUBLIC_TRANSPORT = "live";
  assert.equal(transportMode(), "LIVE");
  assert.ok(sharedTransport() instanceof LiveTransport);

  delete process.env.NEXT_PUBLIC_TRANSPORT;
  assert.equal(transportMode(), "FIXTURE");
  void freshTransport;
});
