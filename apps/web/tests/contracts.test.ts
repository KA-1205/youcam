import assert from "node:assert/strict";
import { test } from "node:test";
import createClient from "openapi-fetch";
import type { paths } from "../../../contracts/runtime/client";
test("typed client preserves fixture labels and server error envelopes", async () => {
  const client = createClient<paths>({ baseUrl: "http://fixture.invalid", fetch: async () => new Response(JSON.stringify({error: {code: "NOT_IMPLEMENTED", message: "Foundation only", details: {}}, requestId: "00000000-0000-4000-8000-000000000001"}), {status: 501, headers: {"Content-Type": "application/json"}}) });
  const { error, response } = await client.GET("/api/sessions/{sessionId}", { params: {path: {sessionId: "00000000-0000-4000-8000-000000000001"}} });
  assert.equal(response.status, 501);
  assert.equal(error?.error.code, "NOT_IMPLEMENTED");
});
